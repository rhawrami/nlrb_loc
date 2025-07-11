import requests
from bs4 import BeautifulSoup
import json
from geopy import Nominatim
import time
import asyncio
import aiohttp
import random
import re
from datetime import datetime

from utils import rand_headers, nlrb_num_iter

def get_most_rec_docs(dat: list):
    '''returns the most recent documents for NLRB_Research cases'''
    name_set = {d['Name'][0] for d in dat}
    rec_dat = []
    for nm in name_set:
        nm_obs = [d for d in dat if d['Name'][0] == nm]
        for obs in nm_obs:
            obs['Date'] = datetime.strptime(obs['Date'],'%Y-%m-%d')
        for obs in nm_obs:
            if obs['Date'] == max([ob['Date'] for ob in nm_obs]) and obs not in rec_dat:
                rec_dat.append(obs)
    for d in rec_dat:
        d['Date'] = d['Date'].date().strftime('%m/%d/%Y')
    return rec_dat

def nlrb_research_get(year=2025):
    '''gets NLRB Research Database Data
    
    :year: year of data
    '''
    num_iter = nlrb_num_iter(year=year)
    base_endpoint = 'https://nlrbresearch.com/NLRB/NLRB_DB'
    query_counter = 0

    if isinstance(year,(list,tuple)):
        yr = ''
        for idx,y in enumerate(year):
            if idx == 0:
                yr += f'"{y}"'
            else:
                yr += f' OR "{y}"'
        search_param = f'Date:{yr}'
    else:
        yr = str(year)
        search_param = f'Date:"{yr}"'

    master_dat = []
    for _ in range(num_iter):
        params = {
            '_search': search_param,
            '_next': query_counter
        }
        r = requests.get(base_endpoint,params=params)
        soup = BeautifulSoup(r.text,'lxml')

        content = soup.find(name='section',class_='content')
        table = content.find(name='table',class_='rows-and-columns')

        headers_html = table.find(name='thead').find(name='tr').find_all('th')
        headers = []
        for header in headers_html:
            headers.append(header.text.strip().replace(r'\n','')) # headers extracted
        headers_dict = {i:headers[i] for i in range(len(headers))}
        
        row_data = []
        trows = table.find(name='tbody').find_all(name='tr')
        for row in trows:
            ctr = 0
            row_dict = {k:None for k in headers_dict.values()}
            for element in row.find_all(name='td'):
                link_check = element.find('a',href=True)
                element_txt = element.text
                if link_check:
                    link = link_check['href']
                    if link.startswith('/'):
                        link = 'https://nlrbresearch.com' + link
                    else:
                        link = link
                    row_dict[headers_dict[ctr]] = (element_txt,link)
                else:
                    row_dict[headers_dict[ctr]] = element_txt
                ctr += 1
            row_data.append(row_dict)
        print(f'Processed NLRB page {_ + 1} / {num_iter}')

        master_dat.extend(row_data)
        query_counter += 100

        time.sleep(1)
    actual_master_dat = {
        'year_query': year,
        'results': master_dat
    }
    return actual_master_dat

def nlrb_to_json(year=2025,fpath=''):
    '''returns nlrb year-queried data as json'''
    dat = nlrb_research_get(year=year)
    with open(fpath,'w') as nlrb_f:
        json.dump(dat,nlrb_f,indent=4)

async def lookup_case_details(url: str,session: aiohttp.ClientSession):
    '''returns dictionary data of Date Filed,Location and Region Assigned
    '''
    try:
        async with session.get(url,headers=rand_headers()) as resp:
            if resp.status != 200:
                print(f'{resp.status} for {url}')
                return None
            
            text = await resp.text()
            soup = BeautifulSoup(text,'lxml')

            content_block = soup.find('div', class_='display-flex flex-justify flex-wrap')
            elements = content_block.find_all('p',class_='margin-0')
            allegations = soup.find('div',id='block-mainpagecontent').find_all('li')
            dat_dict = {
                'Date Filed': None,
                'Status': None,
                'Location': None,
                'Region Assigned': None,
                'Allegations': None
            }
            for i in elements:
                ttl = str(i.find('b').text)
                obs = str(i.text.replace(ttl,'')).strip()
                ttl = ttl.strip().replace(':','')
                if ttl in dat_dict.keys():
                    dat_dict[ttl] = obs
            if allegations:
                if len(allegations) > 0:
                    dat_dict['Allegations'] = [i.text.strip() for i in allegations if 'page\n' not in i.text.lower()]
                else:
                    dat_dict['Allegations'] = allegations[0].text.strip()
            return dat_dict
    
    except Exception as er:
        print(er)
        
async def get_one_case(case,session,geolocator,semaphore,idx):
        try:
            async with semaphore:
                case_det_dict = await lookup_case_details(url=case['CaseNumber'][1],session=session)    
                new_case_dat = {**case,**case_det_dict}

                if new_case_dat['Status'] == 'Closed': # only get open cases
                    return None

                if new_case_dat['Location']:
                    try:
                        location = geolocator.geocode(
                            query=f"{new_case_dat['Location']}, United States",
                            country_codes='us'
                        )
                        if location:
                            new_case_dat['lat_lon'] = (location.latitude, location.longitude)
                            print(f"Processed: {new_case_dat['Name'][0]} (task #{idx})")
                        else:
                            new_case_dat['lat_lon'] = None
                            print(f"No location found for: {new_case_dat['Name'][0]} {case['Location']}")
                    except Exception as er:
                        print(f'Geocoding error: {er}')
                        new_case_dat['lat_lon'] = None
                else:
                    new_case_dat['lat_lon'] = None
                
                await asyncio.sleep(random.uniform(0, 1))
                return new_case_dat
            
        except Exception as er:
            print(f'Error processing case: {er}')
            return None

async def nlrb_final_data(jsonpath='data/nlrb_2025.json',out_json=None):
    '''returns list of case data for map'''
    with open(jsonpath,'r') as nlrb_js:
        dct = json.load(nlrb_js)
    
    yr = dct['year_query']
    dat = dct['results']
    dat = get_most_rec_docs(dat)

    filtered_dat = [case for case in dat if isinstance(case['CaseNumber'], list)]
    print(f'Processing {len(filtered_dat)} cases (Closed cases will be dropped)\n')

    geolocator = Nominatim(user_agent='NLRB_scraper',timeout=30)

    semaphore = asyncio.Semaphore(5)
    connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
    timeout = aiohttp.ClientTimeout(total=30)

    
    async with aiohttp.ClientSession(
            connector=connector, 
            timeout=timeout,
            headers=rand_headers()
    ) as session:
        tasks = [get_one_case(case, session, geolocator, semaphore,idx) for idx,case in enumerate(filtered_dat)]
        cases = await asyncio.gather(*tasks, return_exceptions=True)   

        valid_cases = [case for case in cases if case is not None and not isinstance(case, Exception)]
        print(f'Successfully processed {len(valid_cases)} cases')
        
        if out_json:
            out_dat = {
                'year_query': yr,
                'other_specifications': 'NOTE: only open cases are included; only the most recent document from a case is included',
                'data': valid_cases
            }
            with open(out_json, 'w') as finaldat:
                json.dump(out_dat, finaldat, indent=4)
            print(f'Saved final data to {out_json}')
        
        return valid_cases

async def main(yr=2025):
    '''Main function to orchestrate the data collection'''
    strp_yr = re.sub(r'\[|\]','',str(yr))
    strp_yr = re.sub(r'\, ','_and_',strp_yr)
    nlrb_datf = f'data/nlrb_{strp_yr}.json'

    print(f'\n-------NLRB_Research Collection for years {yr}-------')
    nlrb_to_json(yr, fpath=nlrb_datf)
    print(f'\n-------NLRB_Research Collection Completed-------')

    print(f'\n-------NLRB Case Collection for years {yr}-------')
    final_data = await nlrb_final_data(jsonpath=nlrb_datf, out_json=f'data/map_for_dat_{strp_yr}.json')
    print(f'\n-------NLRB Case Collection Completed-------')
    return final_data

if __name__ == '__main__':
    asyncio.run(main(yr=[2024,2025]))
    
    