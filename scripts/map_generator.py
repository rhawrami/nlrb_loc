import folium
import folium.plugins
import json
import random
from utils import add_time_to_html

'''
POPUP TEMPLATE
'''
POPUP_TEMPLATE = (
    '<html><div style="color:black;">' +
    '<div style="font-size:18px;"><b>{casename}</b></div>' +
    '<div style="font-size:13px;"><i>{location}</i></div>' +
    '<div style="font-size:13px;"><i>{regionassigned} (assigned)</i></div>' +
    '<div style="font-size:13px;"><i>Status</i>: {status}</div>' +
    '<div style="font-size:13px;"><i>Filed</i>: {datefiled}</div>' +
    '<div style="font-size:13px;"><i>Activity</i>: {recentactivity}</div><br>' +
    '<div style="font-size:14px;"><b>Document Type</b>: {doctype}</div>' +
    '<div style="font-size:14px;"><b>Case Number</b>: {casenumber}</div>' +
    '<div style="font-size:14px;"><b>Citation</b>: {citation}</div>' +
    '<div style="font-size:14px;"><b>Circuit</b>: {circuit}</div>' +
    '<div style="font-size:14px;"><b>ALJ</b>: {alj}</div>' +
    '<div style="font-size:14px;"><b>Allegations</b>:{allegations}</div><br>' +
    '<div style="font-size:15px;"><b>{fulldoc}</b></div>' +
    '<div style="font-size:15px;"><b>{aisummary}</b></div>' +
    '<div style="font-size:14px;color:white">_____________________________________________________</div>' +
    '</div></html>'
)

'''
BUILD BASE MAP with plugins
'''
_lawmap = folium.Map(location=(39.8097343, -98.5556199),
                     zoom_control='topright',
                    tiles='Cartodb voyager',
                    zoom_start=5)
# full screen
_fullscreen = folium.plugins.Fullscreen(position='topright')
_fullscreen.add_to(_lawmap)
# tag filter 
tags = [
    'Published Board Decision', 'Unpublished Board Decision', 'ALJ Decision', 'Regional Election Decision',
    'Board Appellate Brief', 'Injunction Appellate Brief', 'GC Memo', 'OM Memo', 'Advice Memo', 'Manual',
    'Statute', 'Circuit Court', 'Supreme Court'
]
_tagfilter = folium.plugins.TagFilterButton(data=tags,
                                            clear_text='Clear DocType Filters')


class NlRbMap:
    '''NLRB cases map generator'''
    def __init__(self,fpath):
        '''Map of NLRB case data
        
        :param fpath: path to json file with data. Expected keys:<br>
            **'year_query'**: year of data<br>
            **'data'**: list of cases
        '''
        with open(fpath,'r') as jsonf:
            rawdat = json.load(jsonf)
        self.year = rawdat['year_query']
        self.cases = rawdat['data']
        self.cases_map = _lawmap
    
    def build_map(self):
        '''build NLRB Research map'''
        fg = folium.FeatureGroup()
        fg.add_to(self.cases_map)
        search_bar = folium.plugins.Search(layer=fg,
                                           search_label='title',
                                           placeholder='Search by NLRB case name and/or location',
                                           color='blue')
        search_bar.add_to(self.cases_map)
        _tagfilter.add_to(_lawmap)

        for case in self.cases:
            if 'Shakeout' in case['Name'][0]:
                continue

            if case['Allegations']:
                if len(case['Allegations']) > 1:
                    case_allegations = '<br>'
                    for allg in case['Allegations']:
                        case_allegations += '- ' + allg + '<br>'
                else:
                    case_allegations = '<br> - ' + case['Allegations'][0]
            else:
                case_allegations =  ' <i>NA</i>'
            case_name = case['Name'][0]
            case_date = case['Date']
            case_location = case['Location']
            case_link = case['Name'][1]
            case_status = case['Status']
            try:
                case_ALJ_name = case['ALJ'][0]
                case_ALJ_link = case['ALJ'][1]
            except IndexError:
                case_ALJ_name = case_ALJ_link = ''
            try:
                case_number_name = case['Citation'][0]
                case_number_link = case['Citation'][1]
            except IndexError:
                case_number_name = case_number_link = ''
            try:
                case_citation_name = case['Citation'][0]
                case_citation_link = case['Citation'][1]
            except IndexError:
                case_citation_name = case_citation_link = ''
            case_summary_link = case['Summary'][1] if not isinstance(case['Summary'], str) else case['Summary']

            mkr_popup = POPUP_TEMPLATE.format(
                casename = f'<a target="_blank" rel="noopener noreferrer" href="{case_link}">{case_name}</a>',
                location = case['Location'],
                regionassigned = case['Region Assigned'],
                doctype = case['Type'],
                status = f"<b>{case_status}</b>",
                datefiled = case['Date Filed'],
                recentactivity = case['Date'],
                alj = f'<a target="_blank" rel="noopener noreferrer" href="{case_ALJ_link}">{case_ALJ_name}</a>' if not isinstance(case['ALJ'],str) else '<i>NA</i>',
                casenumber = f'<a target="_blank" rel="noopener noreferrer" href="{case_number_link}">{case_number_name}</a>',
                citation = f'<a target="_blank" rel="noopener noreferrer" href="{case_citation_link}">{case_citation_name}</a>' if not isinstance(case['Citation'],str) else '<i>NA</i>',
                circuit = case['Circuit'] if not isinstance(case['Circuit'],str) else '<i>NA</i>',
                allegations = case_allegations,
                fulldoc = f'<a target="_blank" rel="noopener noreferrer" href="{case_link}">Read the full document</a>',
                aisummary = f'<a target="_blank" rel="noopener noreferrer" href="{case_summary_link}">Read the AI summary</a>' if not isinstance(case['Summary'],str) else '<i>NA</i>'
            )
            mkr = folium.Marker(
                location=[case['lat_lon'][0] + random.uniform(-.03,.03), # add jitter in case that two cases have same addr
                          case['lat_lon'][1] + random.uniform(-.03,.03)],
                popup=mkr_popup,
                tooltip=folium.Tooltip(text=f"<b>{case_name}</b><br>({case_date})",
                                       style='color:#565656;font-family:Arial, sans-serif;font-size:13px;text-align:center;'),
                icon=folium.plugins.BeautifyIcon(icon_shape='marker',
                                       icon='institution',
                                       text_color="white",
                                       border_width=0,
                                       background_color="#3768aca6"),
                tags=[case['Type']],
                title=f'{case_name} ({case_location})'
            )
            mkr.add_to(fg)

def main(fname='docs/NLRB_map.html'):
    nlrbmap = NlRbMap(fpath='data/map_for_dat_2024_and_2025.json')
    nlrbmap.build_map()
    nlrbmap.cases_map.save(fname)
    add_time_to_html('docs/index.html')


if __name__=='__main__':
    main()

        
    

    
