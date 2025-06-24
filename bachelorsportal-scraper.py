import requests
from bs4 import BeautifulSoup
import json
import time
import csv
from urllib.parse import urljoin, urlparse, parse_qs
import logging
from datetime import datetime
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class BachelorsPortalScraper:
    def __init__(self):
        self.base_url = "https://www.bachelorsportal.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.programs_data = []
        self.universities_data = {}
        
    def get_page(self, url, retry_count=3):
        """Fetch a page with retry logic"""
        for attempt in range(retry_count):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                logging.warning(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logging.error(f"Failed to fetch {url} after {retry_count} attempts")
                    return None
    
    def search_programs(self, country=None, discipline=None, page=1, max_pages=5):
        """Search for bachelor programs with filters"""
        search_url = f"{self.base_url}/search/bachelors"
        params = {
            'page': page,
            'limit': 30  # Items per page
        }
        
        if country:
            params['countries'] = country
        if discipline:
            params['disciplines'] = discipline
            
        all_programs = []
        
        for current_page in range(1, max_pages + 1):
            params['page'] = current_page
            logging.info(f"Fetching page {current_page} for {country or 'all countries'}, {discipline or 'all disciplines'}")
            
            # Construct URL with parameters
            url = f"{search_url}?"
            if country:
                url += f"countries={country}&"
            if discipline:
                url += f"disciplines={discipline}&"
            url += f"page={current_page}"
            
            response = self.get_page(url)
            if not response:
                continue
                
            soup = BeautifulSoup(response.content, 'html.parser')
            programs = self.extract_programs_from_listing(soup)
            
            if not programs:
                logging.info(f"No more programs found on page {current_page}")
                break
                
            all_programs.extend(programs)
            logging.info(f"Extracted {len(programs)} programs from page {current_page}")
            
            # Respectful delay between requests
            time.sleep(2)
            
        return all_programs
    
    def extract_programs_from_listing(self, soup):
        """Extract program information from search results page"""
        programs = []
        
        # Find program cards (adjust selectors based on actual HTML structure)
        program_cards = soup.find_all('div', class_='ProgramCard') or \
                       soup.find_all('article', class_='program-card') or \
                       soup.find_all('div', {'data-role': 'ProgramCard'})
        
        for card in program_cards:
            try:
                program = {}
                
                # Extract title
                title_elem = card.find('h3') or card.find('h2') or card.find('a', class_='title')
                program['title'] = title_elem.text.strip() if title_elem else 'N/A'
                
                # Extract university
                uni_elem = card.find('a', class_='university') or card.find('span', class_='institution')
                program['university'] = uni_elem.text.strip() if uni_elem else 'N/A'
                
                # Extract location
                location_elem = card.find('span', class_='location') or card.find('div', class_='location')
                if location_elem:
                    program['city'] = location_elem.text.strip()
                    program['country'] = location_elem.get('data-country', 'N/A')
                
                # Extract program URL
                link_elem = card.find('a', href=True)
                if link_elem:
                    program['url'] = urljoin(self.base_url, link_elem['href'])
                
                # Extract duration
                duration_elem = card.find('span', class_='duration') or card.find('div', string=lambda x: x and 'years' in x)
                program['duration'] = duration_elem.text.strip() if duration_elem else 'N/A'
                
                # Extract tuition fee
                fee_elem = card.find('span', class_='tuition') or card.find('div', class_='fee')
                program['tuition_fee'] = fee_elem.text.strip() if fee_elem else 'N/A'
                
                # Extract application deadline
                deadline_elem = card.find('span', class_='deadline') or card.find('div', class_='deadline')
                program['deadline'] = deadline_elem.text.strip() if deadline_elem else 'N/A'
                
                programs.append(program)
                
            except Exception as e:
                logging.error(f"Error extracting program: {str(e)}")
                continue
                
        return programs
    
    def scrape_program_details(self, program_url):
        """Scrape detailed information from a program page"""
        response = self.get_page(program_url)
        if not response:
            return None
            
        soup = BeautifulSoup(response.content, 'html.parser')
        details = {}
        
        try:
            # Extract overview
            overview_elem = soup.find('div', class_='overview') or soup.find('section', id='overview')
            if overview_elem:
                details['overview'] = overview_elem.text.strip()
            
            # Extract requirements
            req_section = soup.find('section', id='requirements') or soup.find('div', class_='requirements')
            if req_section:
                requirements = []
                req_items = req_section.find_all('li') or req_section.find_all('div', class_='requirement')
                for item in req_items:
                    requirements.append(item.text.strip())
                details['requirements'] = requirements
            
            # Extract key facts
            facts_section = soup.find('div', class_='key-facts') or soup.find('section', class_='facts')
            if facts_section:
                facts = {}
                fact_items = facts_section.find_all('div', class_='fact-item')
                for item in fact_items:
                    label = item.find('span', class_='label')
                    value = item.find('span', class_='value')
                    if label and value:
                        facts[label.text.strip()] = value.text.strip()
                details['key_facts'] = facts
            
            # Extract disciplines/subjects
            subjects_elem = soup.find('div', class_='disciplines') or soup.find('div', class_='subjects')
            if subjects_elem:
                subjects = [tag.text.strip() for tag in subjects_elem.find_all('a')]
                details['subjects'] = subjects
            
            # Extract language requirements
            lang_elem = soup.find('div', class_='language-requirements')
            if lang_elem:
                details['language_requirements'] = lang_elem.text.strip()
                
        except Exception as e:
            logging.error(f"Error extracting program details: {str(e)}")
            
        return details
    
    def scrape_countries(self):
        """Get list of available countries"""
        url = f"{self.base_url}/countries"
        response = self.get_page(url)
        if not response:
            return []
            
        soup = BeautifulSoup(response.content, 'html.parser')
        countries = []
        
        # Find country links
        country_links = soup.find_all('a', class_='country-link') or \
                       soup.find_all('a', href=lambda x: x and '/study-in-' in x)
        
        for link in country_links:
            country_name = link.text.strip()
            country_code = link.get('data-country-code', '')
            countries.append({
                'name': country_name,
                'code': country_code,
                'url': urljoin(self.base_url, link['href'])
            })
            
        return countries
    
    def scrape_disciplines(self):
        """Get list of available study disciplines"""
        url = f"{self.base_url}/disciplines"
        response = self.get_page(url)
        if not response:
            return []
            
        soup = BeautifulSoup(response.content, 'html.parser')
        disciplines = []
        
        # Find discipline links
        discipline_links = soup.find_all('a', class_='discipline-link') or \
                          soup.find_all('a', href=lambda x: x and '/bachelors-in-' in x)
        
        for link in discipline_links:
            discipline_name = link.text.strip()
            disciplines.append({
                'name': discipline_name,
                'url': urljoin(self.base_url, link['href'])
            })
            
        return disciplines
    
    def save_data(self, data, filename, format='json'):
        """Save scraped data to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format == 'json':
            filepath = f"{filename}_{timestamp}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        elif format == 'csv':
            filepath = f"{filename}_{timestamp}.csv"
            if data and isinstance(data, list):
                keys = data[0].keys()
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=keys)
                    writer.writeheader()
                    writer.writerows(data)
                    
        logging.info(f"Data saved to {filepath}")
        return filepath
    
    def run_targeted_scrape(self, countries=None, disciplines=None, max_programs=100):
        """Run a targeted scrape for specific countries and disciplines"""
        all_programs = []
        
        if not countries:
            # Scrape available countries first
            countries_list = self.scrape_countries()
            countries = [c['name'] for c in countries_list[:10]]  # Top 10 countries
            
        if not disciplines:
            # Scrape available disciplines
            disciplines_list = self.scrape_disciplines()
            disciplines = [d['name'] for d in disciplines_list[:10]]  # Top 10 disciplines
        
        # Scrape programs for each combination
        for country in countries:
            for discipline in disciplines:
                logging.info(f"Scraping programs for {country} - {discipline}")
                programs = self.search_programs(
                    country=country,
                    discipline=discipline,
                    max_pages=2  # Limit pages per search
                )
                
                # Add metadata
                for program in programs:
                    program['search_country'] = country
                    program['search_discipline'] = discipline
                    program['scraped_at'] = datetime.now().isoformat()
                
                all_programs.extend(programs)
                
                if len(all_programs) >= max_programs:
                    break
                    
                time.sleep(3)  # Respectful delay
                
            if len(all_programs) >= max_programs:
                break
        
        # Scrape additional details for subset of programs
        detailed_programs = []
        for i, program in enumerate(all_programs[:20]):  # Detail for first 20
            if 'url' in program:
                logging.info(f"Scraping details for program {i+1}/20: {program['title']}")
                details = self.scrape_program_details(program['url'])
                if details:
                    program.update(details)
                detailed_programs.append(program)
                time.sleep(2)
        
        return {
            'programs': all_programs,
            'detailed_programs': detailed_programs,
            'total_count': len(all_programs),
            'countries': countries,
            'disciplines': disciplines
        }

# Example usage
if __name__ == "__main__":
    scraper = BachelorsPortalScraper()
    
    # Example 1: Scrape programs for specific countries and disciplines
    target_countries = ['Germany', 'Canada', 'Netherlands', 'Australia']
    target_disciplines = ['Computer Science', 'Engineering', 'Business', 'Medicine']
    
    results = scraper.run_targeted_scrape(
        countries=target_countries,
        disciplines=target_disciplines,
        max_programs=200
    )
    
    # Save results
    scraper.save_data(results['programs'], 'bachelors_programs', format='json')
    scraper.save_data(results['programs'], 'bachelors_programs', format='csv')
    
    logging.info(f"Scraping completed! Total programs: {results['total_count']}")
    
    # Example 2: Scrape and analyze data structure
    sample_programs = scraper.search_programs(country='Germany', discipline='Computer Science', max_pages=1)
    if sample_programs:
        print("\nSample program structure:")
        print(json.dumps(sample_programs[0], indent=2))
