from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime
import uuid
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Store conversation sessions
sessions = {}

class DocBot:
    def __init__(self, docs_file: str = 'capillary_docs.json'):
        self.docs_file = docs_file
        self.docs_data = []
        self.load_docs()
    
    def load_docs(self):
        """Load scraped documentation data"""
        if os.path.exists(self.docs_file):
            with open(self.docs_file, 'r', encoding='utf-8') as f:
                self.docs_data = json.load(f)
            logger.info(f"Loaded {len(self.docs_data)} documentation pages")
        else:
            logger.warning(f"Documentation file {self.docs_file} not found. Please run the scraper first.")
    
    def search_docs(self, query: str, max_results: int = 3) -> List[Dict]:
        """Simple keyword-based search in documentation"""
        query_lower = query.lower()
        query_terms = query_lower.split()
        results = []
        
        for doc in self.docs_data:
            score = 0
            title = doc.get('title', '').lower()
            content = doc.get('content', '').lower()
            
            # Score based on title matches (highest weight)
            for term in query_terms:
                if term in title:
                    score += 15
            
            # Score based on exact query match
            if query_lower in title:
                score += 20
            if query_lower in content:
                score += 10
            
            # Score based on individual term frequency in content
            for term in query_terms:
                if len(term) > 2:  # Ignore very short terms
                    score += content.count(term) * 2
            
            # Score based on headings
            for heading in doc.get('headings', []):
                heading_text = heading.get('text', '').lower()
                if query_lower in heading_text:
                    score += 8
                for term in query_terms:
                    if term in heading_text:
                        score += 3
            
            if score > 0:
                results.append({
                    'doc': doc,
                    'score': score
                })
        
        # Sort by score and return top results
        results.sort(key=lambda x: x['score'], reverse=True)
        
        # Log search results for debugging
        logger.info(f"Search for '{query}' found {len(results)} results")
        if results:
            logger.info(f"Top result: {results[0]['doc'].get('title')} (score: {results[0]['score']})")
        
        return [r['doc'] for r in results[:max_results]]
    
    def generate_response(self, query: str, relevant_docs: List[Dict]) -> str:
        """Generate a response based on relevant documentation"""
        if not relevant_docs:
            return ("I couldn't find specific information about that in the documentation. "
                   "Please try rephrasing your question or ask about a different topic.")
        
        # Create a response based on the most relevant document
        top_doc = relevant_docs[0]
        title = top_doc.get('title', 'Documentation')
        content = top_doc.get('content', '')
        
        if not content:
            return ("I found a relevant page but couldn't extract the content. "
                   "Please check the source link below.")
        
        # Start with the title
        response = f"Based on '{title}':\n\n"
        
        # Extract relevant sentences that contain query terms
        query_terms = query.lower().split()
        sentences = content.replace('\n', '. ').split('.')
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        # Find sentences containing query terms
        relevant_sentences = []
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(term in sentence_lower for term in query_terms):
                relevant_sentences.append(sentence)
                if len(relevant_sentences) >= 3:
                    break
        
        # If we found relevant sentences, use them
        if relevant_sentences:
            response += '. '.join(relevant_sentences) + '.'
        else:
            # Fallback: use first meaningful sentences
            meaningful_sentences = [s for s in sentences if len(s) > 30][:4]
            if meaningful_sentences:
                response += '. '.join(meaningful_sentences) + '.'
            else:
                # Last resort: show first 500 characters
                response += content[:500] + '...'
        
        # Add a helpful note
        response += "\n\nFor complete details, please refer to the documentation link below."
        
        return response
    
    def chat(self, message: str) -> tuple[str, List[Dict]]:
        """Process a chat message and return response with sources"""
        relevant_docs = self.search_docs(message)
        response = self.generate_response(message, relevant_docs)
        
        # Format sources
        sources = []
        for doc in relevant_docs:
            sources.append({
                'title': doc.get('title', 'Untitled'),
                'url': doc.get('url', '#')
            })
        
        return response, sources

# Initialize the bot
bot = DocBot()

@app.route('/')
def index():
    """Serve the main HTML page"""
    return render_template('app.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat requests"""
    try:
        data = request.json
        message = data.get('message', '')
        session_id = data.get('session_id')
        
        if not message:
            return jsonify({'error': 'No message provided'}), 400
        
        # Create or get session
        if not session_id or session_id not in sessions:
            session_id = str(uuid.uuid4())
            sessions[session_id] = {
                'created_at': datetime.now().isoformat(),
                'messages': []
            }
        
        # Get bot response
        response, sources = bot.chat(message)
        
        # Store in session
        sessions[session_id]['messages'].append({
            'user': message,
            'assistant': response,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'session_id': session_id,
            'response': response,
            'sources': sources,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/status', methods=['GET'])
def status():
    """Check if documentation is loaded"""
    return jsonify({
        'status': 'ok',
        'docs_loaded': len(bot.docs_data),
        'docs_file_exists': os.path.exists(bot.docs_file)
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    