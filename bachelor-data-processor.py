import json
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import re
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)

class BachelorsDataProcessor:
    """Process scraped data for AI-powered university matching"""
    
    def __init__(self):
        self.processed_programs = []
        self.university_profiles = {}
        self.matching_criteria = {
            'academic': ['gpa', 'test_scores', 'subjects'],
            'financial': ['tuition_range', 'funding_available'],
            'location': ['country', 'city', 'climate'],
            'program': ['discipline', 'duration', 'language'],
            'requirements': ['english_proficiency', 'prerequisites']
        }
    
    def load_scraped_data(self, filepath: str) -> Dict:
        """Load scraped data from JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def extract_tuition_amount(self, tuition_str: str) -> Optional[int]:
        """Extract numeric tuition amount from string"""
        if not tuition_str or tuition_str == 'N/A':
            return None
            
        # Remove currency symbols and extract numbers
        numbers = re.findall(r'[\d,]+', tuition_str)
        if numbers:
            # Take the first number and remove commas
            amount = int(numbers[0].replace(',', ''))
            
            # Convert to EUR if needed (simplified)
            if 'USD' in tuition_str or '$' in tuition_str:
                amount = int(amount * 0.85)  # Rough USD to EUR
            elif 'GBP' in tuition_str or '£' in tuition_str:
                amount = int(amount * 1.15)  # Rough GBP to EUR
                
            return amount
        return None
    
    def parse_duration(self, duration_str: str) -> Optional[int]:
        """Extract duration in months from string"""
        if not duration_str or duration_str == 'N/A':
            return None
            
        # Look for year patterns
        year_match = re.search(r'(\d+)\s*year', duration_str.lower())
        if year_match:
            return int(year_match.group(1)) * 12
            
        # Look for month patterns
        month_match = re.search(r'(\d+)\s*month', duration_str.lower())
        if month_match:
            return int(month_match.group(1))
            
        return None
    
    def extract_language_requirements(self, requirements: Any) -> Dict:
        """Extract language proficiency requirements"""
        lang_reqs = {
            'english_required': False,
            'toefl_min': None,
            'ielts_min': None,
            'duolingo_min': None,
            'other_languages': []
        }
        
        if isinstance(requirements, list):
            req_text = ' '.join(requirements)
        elif isinstance(requirements, str):
            req_text = requirements
        else:
            return lang_reqs
        
        req_text = req_text.lower()
        
        # Check for English requirement
        if 'english' in req_text:
            lang_reqs['english_required'] = True
            
        # Extract TOEFL score
        toefl_match = re.search(r'toefl.*?(\d+)', req_text)
        if toefl_match:
            lang_reqs['toefl_min'] = int(toefl_match.group(1))
            
        # Extract IELTS score
        ielts_match = re.search(r'ielts.*?([\d.]+)', req_text)
        if ielts_match:
            lang_reqs['ielts_min'] = float(ielts_match.group(1))
            
        # Extract Duolingo score
        duolingo_match = re.search(r'duolingo.*?(\d+)', req_text)
        if duolingo_match:
            lang_reqs['duolingo_min'] = int(duolingo_match.group(1))
            
        return lang_reqs
    
    def process_program(self, program: Dict) -> Dict:
        """Process a single program for AI matching"""
        processed = {
            'id': program.get('url', '').split('/')[-1] or f"prog_{hash(program['title'])}",
            'title': program.get('title', 'Unknown Program'),
            'university': program.get('university', 'Unknown University'),
            'country': program.get('country') or program.get('search_country', 'Unknown'),
            'city': program.get('city', 'Unknown'),
            'discipline': program.get('search_discipline', 'Unknown'),
            'duration_months': self.parse_duration(program.get('duration', '')),
            'tuition_eur': self.extract_tuition_amount(program.get('tuition_fee', '')),
            'deadline': program.get('deadline', 'N/A'),
            'url': program.get('url', ''),
            'scraped_at': program.get('scraped_at', datetime.now().isoformat())
        }
        
        # Process requirements if available
        if 'requirements' in program:
            processed['language_requirements'] = self.extract_language_requirements(program['requirements'])
            processed['requirements_text'] = program['requirements'] if isinstance(program['requirements'], str) else ' '.join(program['requirements'])
        
        # Process overview if available
        if 'overview' in program:
            processed['overview'] = program['overview'][:500]  # Limit length
            
        # Process subjects/specializations
        if 'subjects' in program:
            processed['specializations'] = program['subjects']
            
        # Add matching scores placeholders
        processed['matching_scores'] = {
            'academic_fit': 0.0,
            'financial_fit': 0.0,
            'location_fit': 0.0,
            'language_fit': 0.0,
            'overall_fit': 0.0
        }
        
        return processed
    
    def create_university_profile(self, programs: List[Dict]) -> Dict:
        """Create university profiles from program data"""
        university_data = {}
        
        for program in programs:
            uni_name = program['university']
            if uni_name not in university_data:
                university_data[uni_name] = {
                    'name': uni_name,
                    'programs': [],
                    'countries': set(),
                    'cities': set(),
                    'disciplines': set(),
                    'min_tuition': float('inf'),
                    'max_tuition': 0,
                    'avg_tuition': []
                }
            
            uni = university_data[uni_name]
            uni['programs'].append(program['id'])
            uni['countries'].add(program['country'])
            uni['cities'].add(program['city'])
            uni['disciplines'].add(program['discipline'])
            
            if program['tuition_eur']:
                uni['min_tuition'] = min(uni['min_tuition'], program['tuition_eur'])
                uni['max_tuition'] = max(uni['max_tuition'], program['tuition_eur'])
                uni['avg_tuition'].append(program['tuition_eur'])
        
        # Finalize university profiles
        for uni_name, uni in university_data.items():
            uni['countries'] = list(uni['countries'])
            uni['cities'] = list(uni['cities'])
            uni['disciplines'] = list(uni['disciplines'])
            uni['avg_tuition'] = np.mean(uni['avg_tuition']) if uni['avg_tuition'] else None
            if uni['min_tuition'] == float('inf'):
                uni['min_tuition'] = None
                
        return university_data
    
    def prepare_for_ai_matching(self, user_profile: Dict, programs: List[Dict]) -> Dict:
        """Prepare data structure for AI matching analysis"""
        matching_data = {
            'user_profile': {
                'academic': {
                    'gpa': user_profile.get('gpa', 0),
                    'degree_level': user_profile.get('degree_level', ''),
                    'field_of_study': user_profile.get('field_of_study', ''),
                    'test_scores': {
                        'sat': user_profile.get('sat_score'),
                        'toefl': user_profile.get('toefl_score'),
                        'ielts': user_profile.get('ielts_score'),
                        'duolingo': user_profile.get('duolingo_score')
                    }
                },
                'preferences': {
                    'countries': user_profile.get('preferred_countries', []),
                    'budget_eur': user_profile.get('budget_range', 0),
                    'funding_sources': user_profile.get('funding_sources', ''),
                    'disciplines': [user_profile.get('field_of_study', '')]
                },
                'languages': user_profile.get('languages', [])
            },
            'programs': programs,
            'matching_criteria': self.matching_criteria
        }
        
        return matching_data
    
    def calculate_basic_match_scores(self, user_profile: Dict, program: Dict) -> Dict:
        """Calculate basic matching scores (before AI enhancement)"""
        scores = {}
        
        # Academic fit (simplified)
        scores['academic_fit'] = 0.5  # Base score
        
        # Financial fit
        if program['tuition_eur'] and user_profile['preferences']['budget_eur']:
            if program['tuition_eur'] <= user_profile['preferences']['budget_eur']:
                scores['financial_fit'] = 1.0
            else:
                # Gradually decrease score based on how much over budget
                over_budget_ratio = program['tuition_eur'] / user_profile['preferences']['budget_eur']
                scores['financial_fit'] = max(0, 1 - (over_budget_ratio - 1) * 0.5)
        else:
            scores['financial_fit'] = 0.5
        
        # Location fit
        if program['country'] in user_profile['preferences']['countries']:
            scores['location_fit'] = 1.0
        else:
            scores['location_fit'] = 0.3
        
        # Language fit
        lang_req = program.get('language_requirements', {})
        user_scores = user_profile['academic']['test_scores']
        
        if lang_req.get('english_required'):
            language_matches = []
            
            if lang_req.get('toefl_min') and user_scores.get('toefl'):
                language_matches.append(user_scores['toefl'] >= lang_req['toefl_min'])
            
            if lang_req.get('ielts_min') and user_scores.get('ielts'):
                language_matches.append(user_scores['ielts'] >= lang_req['ielts_min'])
                
            if lang_req.get('duolingo_min') and user_scores.get('duolingo'):
                language_matches.append(user_scores['duolingo'] >= lang_req['duolingo_min'])
            
            if language_matches:
                scores['language_fit'] = 1.0 if any(language_matches) else 0.2
            else:
                scores['language_fit'] = 0.5  # No specific requirement found
        else:
            scores['language_fit'] = 1.0  # No language requirement
        
        # Calculate overall fit
        weights = {
            'academic_fit': 0.3,
            'financial_fit': 0.25,
            'location_fit': 0.25,
            'language_fit': 0.2
        }
        
        scores['overall_fit'] = sum(scores[key] * weights[key] for key in weights)
        
        return scores
    
    def process_all_data(self, scraped_data: Dict, sample_user_profile: Dict = None) -> Dict:
        """Process all scraped data and prepare for AI matching"""
        
        # Process programs
        programs = scraped_data.get('programs', [])
        processed_programs = []
        
        for program in programs:
            processed = self.process_program(program)
            
            # Calculate basic match scores if user profile provided
            if sample_user_profile:
                processed['matching_scores'] = self.calculate_basic_match_scores(
                    sample_user_profile, processed
                )
            
            processed_programs.append(processed)
        
        # Create university profiles
        university_profiles = self.create_university_profile(processed_programs)
        
        # Sort programs by overall fit if scores calculated
        if sample_user_profile:
            processed_programs.sort(
                key=lambda x: x['matching_scores']['overall_fit'], 
                reverse=True
            )
        
        # Prepare final output
        output = {
            'metadata': {
                'total_programs': len(processed_programs),
                'total_universities': len(university_profiles),
                'countries': list(set(p['country'] for p in processed_programs)),
                'disciplines': list(set(p['discipline'] for p in processed_programs)),
                'processed_at': datetime.now().isoformat()
            },
            'programs': processed_programs,
            'universities': university_profiles
        }
        
        if sample_user_profile:
            output['matching_data'] = self.prepare_for_ai_matching(
                sample_user_profile, processed_programs[:50]  # Top 50 matches
            )
        
        return output
    
    def save_processed_data(self, data: Dict, output_file: str):
        """Save processed data for AI consumption"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Processed data saved to {output_file}")
        
        # Also save a CSV version of programs for easy viewing
        if 'programs' in data:
            df = pd.DataFrame(data['programs'])
            csv_file = output_file.replace('.json', '_programs.csv')
            df.to_csv(csv_file, index=False)
            logging.info(f"Programs CSV saved to {csv_file}")

# Example usage
if __name__ == "__main__":
    processor = BachelorsDataProcessor()
    
    # Example user profile (from EXPAAI)
    sample_user = {
        'gpa': '3.5',
        'degree_level': 'high_school',
        'field_of_study': 'Computer Science',
        'sat_score': 1400,
        'toefl_score': 95,
        'ielts_score': 7.0,
        'duolingo_score': 120,
        'preferred_countries': ['Germany', 'Canada', 'Netherlands'],
        'budget_range': 15000,  # EUR per year
        'funding_sources': 'self_funded',
        'languages': [
            {'language': 'English', 'proficiency': 'Advanced'},
            {'language': 'German', 'proficiency': 'Beginner'}
        ]
    }
    
    # Load and process scraped data
    try:
        scraped_data = processor.load_scraped_data('bachelors_programs_20240315_120000.json')
        processed_data = processor.process_all_data(scraped_data, sample_user)
        
        # Save processed data
        processor.save_processed_data(processed_data, 'processed_bachelor_programs.json')
        
        # Print top matches
        print("\nTop 10 Matches for User:")
        print("-" * 80)
        for i, program in enumerate(processed_data['programs'][:10], 1):
            print(f"{i}. {program['title']}")
            print(f"   University: {program['university']}")
            print(f"   Country: {program['country']}")
            print(f"   Tuition: €{program['tuition_eur'] or 'N/A'}")
            print(f"   Overall Match: {program['matching_scores']['overall_fit']:.2%}")
            print()
            
    except FileNotFoundError:
        print("No scraped data file found. Please run the scraper first.")
