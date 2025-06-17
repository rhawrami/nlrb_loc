import requests
from bs4 import BeautifulSoup
import random
import re
from datetime import datetime

AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
]

def rand_headers(agents=AGENTS):
    header = {
        'User-Agent': random.choice(agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': random.choice(['en-US,en;q=0.9', 'en-US,en;q=0.8', 'en-GB,en;q=0.9']),
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    if random.choice([True,False]):
        header['DNT'] = '1'
    return header

def nlrb_num_iter(year=2025):
    '''gets required number of iterations for NLRB research'''
    base_endpoint = 'https://nlrbresearch.com/NLRB/NLRB_DB'
    if isinstance(year,(list,tuple)):
        yr = ''
        for idx,y in enumerate(year):
            if idx == 0:
                yr += f'"{y}"'
            else:
                yr += f' OR "{y}"'
        params = {'_search': f'Date:{yr}'}
    else:
        yr = str(year)
        params = {'_search': f'Date:"{yr}"'}
    
    r = requests.get(base_endpoint,params=params)
    soup = BeautifulSoup(r.text,'lxml')
    content = soup.find(name='section',class_='content')
    
    num_docs = content.find_all(name='h3')[-1].text.strip().replace(' documents','').replace(',','') # final h3 header is num documents
    num_docs = int(num_docs)
    if num_docs > 100:
        num_iter = num_docs // 100 + 1 # remainder page too
    else:
        num_iter = 1
    return num_iter

def add_time_to_html(html_path):
    '''inserts update time into html'''
    with open(html_path,'r') as htpath:
        s = htpath.read()
    dtoday = datetime.today().strftime('%m/%d/%Y')
    s_updated = re.sub(r'Last Updated: ..\/..\/....', f'Last Updated: {dtoday}',s)
    with open(html_path,'w') as htpath:
        htpath.write(s_updated)
        
        