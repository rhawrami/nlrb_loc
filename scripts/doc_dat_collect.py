import requests
from bs4 import BeautifulSoup
import json
from geopy import Nominatim
import time

def nlrb_num_iter(year=2025):
    '''gets required number of iterations for NLRB research'''
    base_endpoint = 'https://nlrbresearch.com/NLRB/NLRB_DB'
    yr = str(year)
    params = {'_search': f'Date:"{yr}"'}

    r = requests.get(base_endpoint,params=params)
    soup = BeautifulSoup(r.text,'html.parser')
    content = soup.find(name='section',class_='content')
    
    num_docs = content.find_all(name='h3')[-1].text.strip().replace(' documents','') # final h3 header is num documents
    num_docs = int(num_docs)
    if num_docs > 100:
        num_iter = num_docs // 100 + 1 # remainder page too
    else:
        num_iter = 1
    return num_iter

def nlrb_research_get(year=2025):
    '''gets NLRB Research Database Data
    
    :year: year of data
    '''
    num_iter = nlrb_num_iter(year=year)
    base_endpoint = 'https://nlrbresearch.com/NLRB/NLRB_DB'
    yr = str(year)
    query_counter = 0

    master_dat = []
    for _ in range(num_iter):
        params = {
            '_search': f'Date:"{yr}"',
            '_next': query_counter
        }
        r = requests.get(base_endpoint,params=params)
        soup = BeautifulSoup(r.text,'html.parser')
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
        master_dat.extend(row_data)
        query_counter += 100
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

def lookup_case_details(url=''):
    '''returns dictionary data of Date Filed,Location and Region Assigned
    '''
    r = requests.get(url=url)
    soup = BeautifulSoup(r.text,'html.parser')
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
        

def nlrb_final_data(jsonpath='data/nlrb_2025.json',out_json=None):
    '''returns list of case data for map'''
    with open(jsonpath,'r') as nlrb_js:
        dct = json.load(nlrb_js)
    
    dat = dct['results']
    yr = dct['year_query']
    filtered_dat = [case for case in dat if not isinstance(case['CaseNumber'],str)]
    new_dat = []
    geolocator = Nominatim(user_agent='NLRB_scraper',timeout=30)

    for case in filtered_dat:
        case_det_dict = lookup_case_details(url=case['CaseNumber'][1])
        new_case_dat = {**case,**case_det_dict}
        location = geolocator.geocode(query=f'{new_case_dat['Location']}, United States',
                                      country_codes='us') # redundant i know
        if location:
            new_case_dat['lat_lon'] = (location.latitude,location.longitude)
        else:
            new_case_dat['lat_lon'] = None
        new_dat.append(new_case_dat)
        print(new_case_dat['Name'][0],location.address,'\n',new_case_dat['lat_lon'])
        time.sleep(3)
    if out_json:
        out_dat = {'year_query': yr,
                   'data': new_dat}
        with open(out_json,'w') as finaldat:
            json.dump(out_dat,finaldat,indent=4)

    
if __name__=='__main__':
    nlrb_final_data(out_json='data/final_2025_data.json')
    
    