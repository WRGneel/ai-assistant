"""
Document processor for AI Assistant.
Provides utilities for processing and extracting information from documents.
"""
import re
from typing import List, Dict, Any

class DocumentProcessor:
    """Processor for document content"""
    def __init__(self):
        pass

    def chunk_document(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split document into chunks for processing"""
        chunks = []
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            # Try to find a good break point (period, newline, etc.)
            if end < len(text):
                # Look for a period or newline within the last 100 chars of the chunk
                for i in range(end, max(end - 100, start), -1):
                    if text[i] in ['.', '\n', '!', '?']:
                        end = i + 1
                        break

            chunks.append(text[start:end])
            start = end - overlap  # Create overlap

        return chunks

    def summarize_text(self, text: str, max_sentences: int = 5) -> str:
        """Simple extractive summarization - selects important sentences"""
        # Split text into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)

        # If text is short, return it as is
        if len(sentences) <= max_sentences:
            return text

        # Simple heuristic: score sentences based on length and position
        scored_sentences = []
        for i, sentence in enumerate(sentences):
            # Score based on length (longer sentences might contain more info)
            length_score = min(1.0, len(sentence) / 100.0)

            # Score based on position (first and last sentences often important)
            position = i / len(sentences)
            position_score = 1.0 if position < 0.2 or position > 0.8 else 0.5

            # Score based on presence of important words
            important_words = ['important', 'significant', 'key', 'main', 'essential', 'critical']
            content_score = any(word in sentence.lower() for word in important_words)

            # Combined score
            score = length_score + position_score + (0.5 if content_score else 0)

            scored_sentences.append((i, sentence, score))

        # Sort by score, then by original position
        scored_sentences.sort(key=lambda x: (-x[2], x[0]))

        # Select top sentences
        selected_sentences = scored_sentences[:max_sentences]

        # Sort back to original order
        selected_sentences.sort(key=lambda x: x[0])

        # Join sentences
        summary = ' '.join(s[1] for s in selected_sentences)

        return summary

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract entities (people, organizations, locations) from text"""
        # This is a simplified implementation for demonstration
        # In a real implementation, you might use NER libraries

        entities = {
            "people": [],
            "organizations": [],
            "locations": []
        }

        # Simple regex patterns for demonstration
        # People: Capitalized names
        people_pattern = r'(?<!\w)[A-Z][a-z]+ [A-Z][a-z]+'
        entities["people"] = list(set(re.findall(people_pattern, text)))

        # Organizations: Capitalized sequences followed by Inc, Corp, etc.
        org_pattern = r'[A-Z][a-zA-Z]+ (?:Inc|Corp|LLC|Company|Organization)'
        entities["organizations"] = list(set(re.findall(org_pattern, text)))

        # Locations: Common location prefixes
        loc_pattern = r'(?:in|at|from|to) ([A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)*)'
        loc_matches = re.findall(loc_pattern, text)
        entities["locations"] = list(set(match for match in loc_matches if match.strip()))

        return entities

    def format_entity_list(self, entities: Dict[str, List[str]]) -> str:
        """Format entity list for display"""
        result = "Extracted Entities:\n\n"

        for entity_type, entity_list in entities.items():
            if entity_list:
                result += f"{entity_type.title()}:\n"
                for entity in entity_list:
                    result += f"  - {entity}\n"
                result += "\n"
            else:
                result += f"No {entity_type} found.\n\n"

        return result

    def extract_statistics(self, text: str) -> Dict[str, List[str]]:
        """Extract statistical data from text"""
        statistics = {
            "percentages": [],
            "monetary": [],
            "numerical": []
        }

        # Percentage pattern
        pct_pattern = r'\b\d+(?:\.\d+)?%'
        statistics["percentages"] = list(set(re.findall(pct_pattern, text)))

        # Monetary pattern
        money_pattern = r'\$\d+(?:,\d+)*(?:\.\d+)?|\d+(?:,\d+)*(?:\.\d+)? dollars'
        statistics["monetary"] = list(set(re.findall(money_pattern, text)))

        # General numerical pattern (with context)
        num_pattern = r'\b\d+(?:,\d+)*(?:\.\d+)? [a-zA-Z]+'
        statistics["numerical"] = list(set(re.findall(num_pattern, text)))

        return statistics

    def format_statistics(self, statistics: Dict[str, List[str]]) -> str:
        """Format statistics for display"""
        result = "Extracted Statistics:\n\n"

        for stat_type, stat_list in statistics.items():
            if stat_list:
                result += f"{stat_type.title()}:\n"
                for stat in stat_list:
                    result += f"  - {stat}\n"
                result += "\n"
            else:
                result += f"No {stat_type} found.\n\n"

        return result

    def extract_timeline(self, text: str) -> List[Dict[str, str]]:
        """Extract timeline events from text"""
        # Simple date pattern matcher
        date_patterns = [
            r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?) \d{1,2},? \d{4}',
            r'\d{1,2} (?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?),? \d{4}',
            r'\d{4}-\d{2}-\d{2}',
            r'\d{2}/\d{2}/\d{4}'
        ]

        timeline = []

        # Find dates and surrounding context
        for pattern in date_patterns:
            for match in re.finditer(pattern, text):
                date = match.group(0)

                # Get context (up to 100 chars after the date)
                start_idx = match.end()
                end_idx = min(start_idx + 100, len(text))
                context = text[start_idx:end_idx].strip()

                # Try to extract a full sentence
                sentence_end = re.search(r'[.!?]', context)
                if sentence_end:
                    context = context[:sentence_end.end()]

                if context:
                    timeline.append({
                        "date": date,
                        "event": context
                    })

        # Sort by date (simple string sorting - not ideal but works for demo)
        timeline.sort(key=lambda x: x["date"])

        return timeline

    def format_timeline(self, timeline: List[Dict[str, str]]) -> str:
        """Format timeline for display"""
        if not timeline:
            return "No timeline events extracted."

        result = "Timeline of Events:\n\n"

        for event in timeline:
            result += f"{event['date']}: {event['event']}\n\n"

        return result