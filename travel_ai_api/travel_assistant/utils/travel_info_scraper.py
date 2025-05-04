"""
Travel information scraping utility for Travel AI assistant.

This module provides functions to scrape visa requirements, travel advisories,
health information, and other travel-related data for various destinations.
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import logging
import random
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Common user agents for rotating
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0'
]


class TravelInfoScraper:
    """A class for scraping visa and travel requirement information"""
    
    def __init__(self, timeout=15, max_retries=3):
        self.timeout = timeout
        self.max_retries = max_retries
    
    def get_random_user_agent(self) -> str:
        """Return a random user agent to avoid detection"""
        return random.choice(USER_AGENTS)
    
    def make_request(self, url: str, headers=None, params=None) -> Optional[requests.Response]:
        """Make HTTP request with retry logic"""
        if headers is None:
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml'
            }
            
        retries = 0
        while retries < self.max_retries:
            try:
                response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                retries += 1
                if retries >= self.max_retries:
                    logger.error(f"Failed to retrieve {url} after {self.max_retries} attempts: {e}")
                    return None
                
                logger.warning(f"Attempt {retries} failed. Retrying in {retries * 2} seconds...")
                time.sleep(retries * 2)
        return None
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if text is None:
            return ""
        return re.sub(r'\s+', ' ', text).strip()
    
    def get_visa_requirements(self, from_country: str, to_country: str) -> Dict[str, Any]:
        """
        Get visa requirements for travel between two countries.
        Uses data from VisaHQ and other sources.
        
        Args:
            from_country: Country of origin/citizenship
            to_country: Destination country
            
        Returns:
            Dictionary with visa requirement information
        """
        # Normalize country names for URL
        from_country = from_country.lower().replace(' ', '-')
        to_country = to_country.lower().replace(' ', '-')
        
        # Try to get data from VisaHQ
        visa_info = self._scrape_visahq(from_country, to_country)
        
        if not visa_info or not visa_info.get('requirement'):
            # Fallback to alternative source
            passport_index_info = self._scrape_passport_index(from_country, to_country)
            if passport_index_info:
                visa_info = passport_index_info
        
        # If we still don't have info, try travel.state.gov (US-specific)
        if not visa_info or not visa_info.get('requirement'):
            state_gov_info = self._scrape_state_gov(to_country)
            if state_gov_info:
                visa_info = state_gov_info
        
        # If we couldn't find info from any source, return placeholder
        if not visa_info:
            visa_info = {
                'from_country': from_country.replace('-', ' ').title(),
                'to_country': to_country.replace('-', ' ').title(),
                'requirement': 'Unknown',
                'description': 'Could not find visa requirement information. Please check with the embassy or consulate of the destination country.',
                'source': 'N/A'
            }
        
        return visa_info
    
    def _scrape_visahq(self, from_country: str, to_country: str) -> Optional[Dict[str, Any]]:
        """Scrape visa information from VisaHQ"""
        url = f"https://www.visahq.com/{from_country}/visa-requirements-to-{to_country}"
        
        logger.info(f"Scraping visa information for {from_country} → {to_country} from VisaHQ")
        response = self.make_request(url)
        if not response:
            return None
        
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the main visa requirement info
            requirement_elem = soup.select_one("div.requirement span.center")
            if not requirement_elem:
                return None
                
            requirement = self.clean_text(requirement_elem.text)
            
            # Find the description/details
            details_elem = soup.select_one("div.requirement-text")
            details = self.clean_text(details_elem.text) if details_elem else ""
            
            # Get validity info if available
            validity_elem = soup.select_one("div.validity")
            validity = self.clean_text(validity_elem.text) if validity_elem else ""
            
            # Get processing time if available
            processing_elem = soup.select_one("div.processing")
            processing = self.clean_text(processing_elem.text) if processing_elem else ""
            
            return {
                'from_country': from_country.replace('-', ' ').title(),
                'to_country': to_country.replace('-', ' ').title(),
                'requirement': requirement,
                'description': details,
                'validity': validity,
                'processing_time': processing,
                'source': 'VisaHQ'
            }
            
        except Exception as e:
            logger.error(f"Error scraping VisaHQ: {e}")
            return None
    
    def _scrape_passport_index(self, from_country: str, to_country: str) -> Optional[Dict[str, Any]]:
        """Scrape visa information from Passport Index"""
        url = f"https://www.passportindex.org/passport/{from_country}/"
        
        logger.info(f"Scraping visa information for {from_country} → {to_country} from Passport Index")
        response = self.make_request(url)
        if not response:
            return None
        
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the table with visa requirements
            visa_table = soup.select_one("table.visa-requirements")
            if not visa_table:
                return None
                
            rows = visa_table.select("tr")
            for row in rows:
                country_elem = row.select_one("td.country")
                if not country_elem:
                    continue
                    
                country_name = self.clean_text(country_elem.text).lower()
                if to_country.replace('-', ' ') in country_name:
                    requirement_elem = row.select_one("td.requirement")
                    if requirement_elem:
                        requirement = self.clean_text(requirement_elem.text)
                        
                        return {
                            'from_country': from_country.replace('-', ' ').title(),
                            'to_country': to_country.replace('-', ' ').title(),
                            'requirement': requirement,
                            'description': f"Based on Passport Index data, travelers from {from_country.replace('-', ' ').title()} to {to_country.replace('-', ' ').title()} require: {requirement}",
                            'source': 'Passport Index'
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Error scraping Passport Index: {e}")
            return None
    
    def _scrape_state_gov(self, to_country: str) -> Optional[Dict[str, Any]]:
        """Scrape visa information from US Department of State (for US citizens)"""
        # Format country name for URL
        country_url = to_country.lower().replace(' ', '-').replace('.', '')
        url = f"https://travel.state.gov/content/travel/en/international-travel/International-Travel-Country-Information-Pages/{country_url}.html"
        
        logger.info(f"Scraping visa information for US → {to_country} from travel.state.gov")
        response = self.make_request(url)
        if not response:
            return None
        
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the entry requirements section
            entry_section = None
            headings = soup.select("h2, h3")
            
            for heading in headings:
                if "entry" in heading.text.lower() and "requirements" in heading.text.lower():
                    entry_section = heading
                    break
            
            if not entry_section:
                return None
                
            # Get the content following this heading
            content = []
            elem = entry_section.find_next()
            
            while elem and elem.name != 'h2' and elem.name != 'h3':
                if elem.name == 'p' or elem.name == 'li':
                    content.append(self.clean_text(elem.text))
                elem = elem.find_next()
            
            if not content:
                return None
                
            # Determine the requirement based on content
            requirement = "Required"  # Default
            content_text = ' '.join(content).lower()
            
            if "not require a visa" in content_text or "visa is not required" in content_text:
                requirement = "Visa-free"
            elif "visa on arrival" in content_text:
                requirement = "Visa on arrival"
            elif "electronic visa" in content_text or "e-visa" in content_text:
                requirement = "e-Visa available"
                
            return {
                'from_country': 'United States',
                'to_country': to_country.replace('-', ' ').title(),
                'requirement': requirement,
                'description': '\n'.join(content),
                'source': 'US Department of State'
            }
            
        except Exception as e:
            logger.error(f"Error scraping travel.state.gov: {e}")
            return None
    
    def get_travel_advisories(self, country: str) -> Dict[str, Any]:
        """
        Get travel advisories and safety information for a country.
        
        Args:
            country: Country name
            
        Returns:
            Dictionary with travel advisory information
        """
        # Try to get data from multiple sources
        country_formatted = country.lower().replace(' ', '-')
        
        # Try US State Department
        us_advisory = self._scrape_us_advisory(country_formatted)
        
        # Try UK Foreign Office
        uk_advisory = self._scrape_uk_advisory(country_formatted)
        
        # Combine the results
        advisories = {
            'country': country.title(),
            'advisories': []
        }
        
        if us_advisory:
            advisories['advisories'].append(us_advisory)
            
        if uk_advisory:
            advisories['advisories'].append(uk_advisory)
            
        if not advisories['advisories']:
            advisories['advisories'].append({
                'source': 'No data available',
                'level': 'Unknown',
                'summary': 'No travel advisory information found. Please check with your country\'s foreign office or department of state.',
                'last_updated': None
            })
        
        return advisories
    
    def _scrape_us_advisory(self, country: str) -> Optional[Dict[str, Any]]:
        """Scrape US travel advisory from travel.state.gov"""
        url = f"https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories/{country}-travel-advisory.html"
        
        logger.info(f"Scraping US travel advisory for {country} from travel.state.gov")
        response = self.make_request(url)
        if not response:
            return None
        
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the advisory level
            alert_elem = soup.select_one("div.tsg-alert-content")
            if not alert_elem:
                return None
                
            alert_text = self.clean_text(alert_elem.text)
            
            # Extract level
            level_match = re.search(r'Level (\d+)', alert_text)
            level = level_match.group(0) if level_match else "Unknown"
            
            # Find the last updated date
            date_elem = soup.select_one("div.updated-date")
            last_updated = self.clean_text(date_elem.text).replace('Last Update:', '').strip() if date_elem else None
            
            # Find the advisory content
            content_elem = soup.select_one("div#detailed-advisory-content")
            summary = self.clean_text(content_elem.get_text()) if content_elem else alert_text
            
            return {
                'source': 'US Department of State',
                'level': level,
                'summary': summary,
                'last_updated': last_updated
            }
            
        except Exception as e:
            logger.error(f"Error scraping US travel advisory: {e}")
            return None
    
    def _scrape_uk_advisory(self, country: str) -> Optional[Dict[str, Any]]:
        """Scrape UK travel advisory from GOV.UK"""
        url = f"https://www.gov.uk/foreign-travel-advice/{country}"
        
        logger.info(f"Scraping UK travel advisory for {country} from GOV.UK")
        response = self.make_request(url)
        if not response:
            return None
        
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the summary section
            summary_elem = soup.select_one("div.govuk-summary-card__content")
            if not summary_elem:
                return None
                
            summary = self.clean_text(summary_elem.get_text())
            
            # Find the last updated date
            date_elem = soup.select_one("div.app-c-updated-date")
            last_updated = self.clean_text(date_elem.text).replace('Updated:', '').strip() if date_elem else None
            
            # Try to determine advisory level from content
            level = "See summary"
            if "advise against all travel" in summary.lower():
                level = "Advise against all travel"
            elif "advise against all but essential travel" in summary.lower():
                level = "Advise against all but essential travel"
            
            return {
                'source': 'UK Foreign Office',
                'level': level,
                'summary': summary,
                'last_updated': last_updated
            }
            
        except Exception as e:
            logger.error(f"Error scraping UK travel advisory: {e}")
            return None
    
    def get_health_information(self, country: str) -> Dict[str, Any]:
        """
        Get health and vaccination information for a country.
        
        Args:
            country: Country name
            
        Returns:
            Dictionary with health information
        """
        country_formatted = country.lower().replace(' ', '-')
        
        # Try to get CDC information (or another reliable source)
        cdc_info = self._scrape_cdc_health_info(country_formatted)
        
        # If we couldn't find info, return placeholder
        if not cdc_info:
            return {
                'country': country.title(),
                'vaccinations': [],
                'health_risks': [],
                'summary': 'Could not find specific health information. Please consult with a travel health specialist or your doctor before traveling.',
                'source': 'N/A'
            }
        
        return cdc_info
    
    def _scrape_cdc_health_info(self, country: str) -> Optional[Dict[str, Any]]:
        """Scrape health information from CDC Travelers' Health"""
        url = f"https://wwwnc.cdc.gov/travel/destinations/traveler/none/{country}"
        
        logger.info(f"Scraping health information for {country} from CDC")
        response = self.make_request(url)
        if not response:
            return None
        
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the vaccinations section
            vaccinations = []
            vax_section = soup.find(id='vaccines-and-medicines')
            if vax_section:
                vax_list = vax_section.find_next('ul')
                if vax_list:
                    for item in vax_list.find_all('li'):
                        vaccinations.append(self.clean_text(item.text))
            
            # Find health risks section
            health_risks = []
            risks_section = soup.find(id='non-vaccine-recommendations')
            if risks_section:
                risks_list = risks_section.find_next('ul')
                if risks_list:
                    for item in risks_list.find_all('li'):
                        health_risks.append(self.clean_text(item.text))
            
            # Find the summary
            summary_section = soup.find(id='destination-content')
            summary = ""
            if summary_section:
                summary_paras = summary_section.find_all('p', limit=2)
                summary = ' '.join([self.clean_text(p.text) for p in summary_paras])
            
            return {
                'country': country.replace('-', ' ').title(),
                'vaccinations': vaccinations,
                'health_risks': health_risks,
                'summary': summary,
                'source': 'CDC Travelers\' Health'
            }
            
        except Exception as e:
            logger.error(f"Error scraping CDC health information: {e}")
            return None
    
    def get_travel_info(self, from_country: str, to_country: str) -> Dict[str, Any]:
        """
        Get comprehensive travel information for traveling from one country to another.
        
        Args:
            from_country: Country of origin/citizenship
            to_country: Destination country
            
        Returns:
            Dictionary with comprehensive travel information
        """
        # Get visa requirements
        visa_info = self.get_visa_requirements(from_country, to_country)
        
        # Get travel advisories
        advisory_info = self.get_travel_advisories(to_country)
        
        # Get health information
        health_info = self.get_health_information(to_country)
        
        # Combine all information
        return {
            'from_country': from_country.title(),
            'to_country': to_country.title(),
            'visa': visa_info,
            'advisories': advisory_info,
            'health': health_info,
            'retrieved_at': datetime.now().isoformat()
        }


# Example usage
if __name__ == "__main__":
    scraper = TravelInfoScraper()
    
    # Example: Get travel information for US citizen going to Japan
    travel_info = scraper.get_travel_info(from_country="United States", to_country="Japan")
    
    print("\n=== TRAVEL INFORMATION ===")
    print(f"From: {travel_info['from_country']} to {travel_info['to_country']}")
    
    print("\nVISA REQUIREMENTS:")
    print(f"Requirement: {travel_info['visa']['requirement']}")
    print(f"Details: {travel_info['visa']['description']}")
    
    print("\nTRAVEL ADVISORIES:")
    for advisory in travel_info['advisories']['advisories']:
        print(f"Source: {advisory['source']}")
        print(f"Level: {advisory['level']}")
        print(f"Summary: {advisory['summary'][:150]}...")
        
    print("\nHEALTH INFORMATION:")
    print(f"Summary: {travel_info['health']['summary'][:150]}...")
    if travel_info['health']['vaccinations']:
        print("Recommended Vaccinations:")
        for vax in travel_info['health']['vaccinations'][:3]:
            print(f"- {vax}")
