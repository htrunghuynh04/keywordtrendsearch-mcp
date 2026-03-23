from serpapi import GoogleSearch
from itertools import zip_longest
import json, csv
import re
from collections import Counter


class SeoKeywordResearch:
    def __init__(self, query: str, api_key: str, lang: str = 'en', country: str = 'us', domain: str = 'google.com') -> None:
        self.query = query
        self.api_key = api_key
        self.lang = lang
        self.country = country
        self.domain = domain
        self.__related_questions_results = []


    def get_auto_complete(self) -> list:
        params = {
            'api_key': self.api_key,            # https://serpapi.com/manage-api-key
            'engine': 'google_autocomplete',    # search engine
            'q': self.query,                    # search query
            'gl': self.country,                 # country of the search
            'hl': self.lang                     # language of the search
        }

        search = GoogleSearch(params)           # data extraction on the SerpApi backend
        results = search.get_dict()             # JSON -> Python dict
        
        auto_complete_results = [result.get('value') for result in results.get('suggestions', [])]
        
        return auto_complete_results


    def get_related_searches(self) -> list:
        params = {
            'api_key': self.api_key,            # https://serpapi.com/manage-api-key
            'engine': 'google',                 # search engine
            'q': self.query,                    # search query
            'google_domain': self.domain,       # Google domain to use
            'gl': self.country,                 # country of the search
            'hl': self.lang                     # language of the search
        }

        search = GoogleSearch(params)           # data extraction on the SerpApi backend
        results = search.get_dict()             # JSON -> Python dict
        
        related_searches_results = [result.get('query') for result in results.get('related_searches', [])]

        return related_searches_results


    def __get_depth_results(self, token: str, depth: int) -> None:
        '''
        This function allows you to extract more data from People Also Ask.
        
        The function takes the following arguments:
        
        :param token: allows access to additional related questions.
        :param depth: limits the input depth for each related question.
        '''

        depth_params = {
            'api_key': self.api_key,
            'engine': 'google_related_questions',
            'next_page_token': token,
        }

        depth_search = GoogleSearch(depth_params)
        depth_results = depth_search.get_dict()
        
        self.__related_questions_results.extend([result.get('question') for result in depth_results.get('related_questions', [])])
        
        if depth > 1:
            for question in depth_results.get('related_questions', []):
                if question.get('next_page_token'):
                    self.__get_depth_results(question.get('next_page_token'), depth - 1)


    def get_related_questions(self, depth_limit: int = 0) -> list:
        params = {
            'api_key': self.api_key,            # https://serpapi.com/manage-api-key
            'engine': 'google',                 # search engine
            'q': self.query,                    # search query
            'google_domain': self.domain,       # Google domain to use
            'gl': self.country,                 # country of the search
            'hl': self.lang                     # language of the search
        }

        search = GoogleSearch(params)           # data extraction on the SerpApi backend
        results = search.get_dict()             # JSON -> Python dict

        self.__related_questions_results = [result.get('question') for result in results.get('related_questions', [])]

        if depth_limit > 4:
            depth_limit = 4

        if depth_limit:      
            for question in results.get('related_questions', []):
                if question.get('next_page_token'):
                    self.__get_depth_results(question.get('next_page_token'), depth_limit)
            
        return self.__related_questions_results


    def select_target_keywords(self, depth_limit: int = 1) -> dict:
        '''
        Aggregates keyword data from all sources, scores candidates, and selects
        1 primary keyword and 3-5 secondary keywords (semantic, long-tail, variations).

        Scoring is based on:
        - Cross-source frequency (appears in autocomplete + related searches + questions)
        - Position signal (higher position in autocomplete = more popular)
        - Relevance to seed query (word overlap)
        - Long-tail bonus (longer phrases often have less competition)

        Returns a dict with primary_keyword, secondary_keywords, and all_candidates.
        '''
        auto_complete = self.get_auto_complete()
        related_searches = self.get_related_searches()
        related_questions = self.get_related_questions(depth_limit)

        # Extract keyword phrases from questions (remove question words)
        question_keywords = self._extract_keywords_from_questions(related_questions)

        # Build candidate pool with source tracking
        candidates = {}  # keyword -> {sources, positions, score}

        for i, kw in enumerate(auto_complete):
            kw_lower = kw.lower().strip()
            if kw_lower and kw_lower != self.query.lower():
                if kw_lower not in candidates:
                    candidates[kw_lower] = {'sources': set(), 'ac_position': None, 'original': kw}
                candidates[kw_lower]['sources'].add('autocomplete')
                candidates[kw_lower]['ac_position'] = i

        for kw in related_searches:
            kw_lower = kw.lower().strip()
            if kw_lower and kw_lower != self.query.lower():
                if kw_lower not in candidates:
                    candidates[kw_lower] = {'sources': set(), 'ac_position': None, 'original': kw}
                candidates[kw_lower]['sources'].add('related_searches')

        for kw in question_keywords:
            kw_lower = kw.lower().strip()
            if kw_lower and kw_lower != self.query.lower():
                if kw_lower not in candidates:
                    candidates[kw_lower] = {'sources': set(), 'ac_position': None, 'original': kw}
                candidates[kw_lower]['sources'].add('related_questions')

        if not candidates:
            return {
                'seed_query': self.query,
                'primary_keyword': None,
                'secondary_keywords': [],
                'all_candidates': [],
                'raw_data': {
                    'auto_complete': auto_complete,
                    'related_searches': related_searches,
                    'related_questions': related_questions,
                }
            }

        # Score each candidate
        seed_words = set(self.query.lower().split())
        scored = []

        for kw, info in candidates.items():
            score = 0.0
            kw_words = set(kw.split())
            word_count = len(kw_words)

            # Cross-source frequency (max 30 points)
            score += len(info['sources']) * 10

            # Autocomplete position signal (max 10 points, top positions score higher)
            if info['ac_position'] is not None:
                score += max(0, 10 - info['ac_position'])

            # Relevance: word overlap with seed query (max 20 points)
            overlap = len(seed_words & kw_words)
            if seed_words:
                score += (overlap / len(seed_words)) * 20

            # Long-tail bonus: 3+ words get a bonus (max 10 points)
            if word_count >= 3:
                score += min(word_count - 2, 3) * 3

            # Classify keyword type
            kw_type = self._classify_keyword(kw_words, seed_words, word_count)

            scored.append({
                'keyword': info['original'],
                'score': round(score, 1),
                'sources': sorted(info['sources']),
                'type': kw_type,
                'word_count': word_count,
            })

        # Sort by score descending
        scored.sort(key=lambda x: x['score'], reverse=True)

        # Select primary: highest scoring keyword
        primary = scored[0]

        # Select secondary: next best keywords, prefer diversity of types
        secondary = []
        seen_types = set()
        for candidate in scored[1:]:
            if len(secondary) >= 5:
                break
            # Prefer diverse types, but accept same type if we haven't filled 3 yet
            if candidate['type'] not in seen_types or len(secondary) < 3:
                secondary.append(candidate)
                seen_types.add(candidate['type'])

        return {
            'seed_query': self.query,
            'primary_keyword': primary,
            'secondary_keywords': secondary,
            'all_candidates': scored,
            'raw_data': {
                'auto_complete': auto_complete,
                'related_searches': related_searches,
                'related_questions': related_questions,
            }
        }


    def _extract_keywords_from_questions(self, questions: list) -> list:
        '''Extract keyword phrases from "People Also Ask" questions.'''
        question_words = re.compile(
            r'^(what|how|why|when|where|which|who|whom|whose|is|are|was|were|do|does|did|can|could|should|would|will)\s+',
            re.IGNORECASE
        )
        keywords = []
        for q in questions:
            if not q:
                continue
            # Remove question mark and leading question words
            cleaned = q.rstrip('?').strip()
            cleaned = question_words.sub('', cleaned).strip()
            if cleaned:
                keywords.append(cleaned)
        return keywords


    def _classify_keyword(self, kw_words: set, seed_words: set, word_count: int) -> str:
        '''Classify a keyword as semantic, long-tail, or variation.'''
        overlap = len(seed_words & kw_words)

        if word_count >= 4:
            return 'long-tail'
        elif overlap == 0 or (seed_words and overlap / len(seed_words) < 0.3):
            return 'semantic'
        else:
            return 'variation'


    def save_to_csv(self, data: dict) -> None:
        with open(f'{self.query.replace(" ", "_")}.csv', 'w') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(data.keys())
            writer.writerows(zip_longest(*data.values()))


    def save_to_json(self, data: dict) -> None:
        with open(f'{self.query.replace(" ", "_")}.json', 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, indent=2, ensure_ascii=False)


    def save_to_txt(self, data: dict) -> None:
        with open(f'{self.query.replace(" ", "_")}.txt', 'w') as txt_file:
            for key in data.keys():
                txt_file.write('\n'.join(data.get(key)) + '\n')


    def print_data(self, data: dict) -> None:
        print(json.dumps(data, indent=2, ensure_ascii=False))