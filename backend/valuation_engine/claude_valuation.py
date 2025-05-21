import os
import json
import anthropic
import hashlib
from dotenv import load_dotenv
from functools import lru_cache
from tqdm import tqdm
import re
import time

# Load environment variables
load_dotenv()

# Initialize Anthropic client with API key
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def get_equipment_hash(row):
    """Create a unique hash for an equipment item"""
    item_str = f"{row['Unit #']}|{row['Description']}"
    
    # Add optional fields if they exist
    if 'Year' in row and not pd.isna(row['Year']):
        item_str += f"|{row['Year']}"
    if 'Condition' in row and not pd.isna(row['Condition']):
        item_str += f"|{row['Condition']}"
        
    return hashlib.md5(item_str.encode()).hexdigest()

@lru_cache(maxsize=1000)
def get_cached_valuation(equipment_hash):
    """Retrieve cached valuation if available"""
    cache_dir = "./cache"
    os.makedirs(cache_dir, exist_ok=True)
    
    cache_path = f"{cache_dir}/{equipment_hash}.json"
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

def save_to_cache(equipment_hash, result):
    """Save valuation result to cache"""
    cache_dir = "./cache"
    os.makedirs(cache_dir, exist_ok=True)
    
    cache_path = f"{cache_dir}/{equipment_hash}.json"
    with open(cache_path, 'w') as f:
        json.dump(result, f)

def parse_claude_response(response_content):
    """Parse JSON from Claude's response"""
    # First try to extract JSON block if it exists
    json_match = re.search(r'```json\n(.*?)\n```', response_content, re.DOTALL)
    
    if json_match:
        json_str = json_match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    # If that fails, try to find any JSON-like structure
    try:
        # Find the first { and last } in the response
        start = response_content.find('{')
        end = response_content.rfind('}')
        
        if start != -1 and end != -1 and end > start:
            json_str = response_content[start:end+1]
            return json.loads(json_str)
    except:
        pass
    
    # Return raw response as fallback
    return {"raw_response": response_content}

def process_equipment_item(row):
    """
    Process a single equipment item with Claude
    
    Args:
        row: DataFrame row with equipment details
        
    Returns:
        Dictionary with valuation results
    """
    # Create hash for caching
    item_hash = get_equipment_hash(row)
    
    # Check cache first
    cached_result = get_cached_valuation(item_hash)
    if cached_result:
        return cached_result
    
    # Prepare prompt with available fields
    prompt = f"""
    I need a detailed valuation for this equipment:
    - Unit #: {row['Unit #']}
    - Description: {row['Description']}
    """
    
    # Add optional fields
    if 'Year' in row and not pd.isna(row['Year']):
        prompt += f"- Year: {row['Year']}\n"
    if 'Location' in row and not pd.isna(row['Location']):
        prompt += f"- Location: {row['Location']}\n"
    if 'Condition' in row and not pd.isna(row['Condition']):
        prompt += f"- Condition: {row['Condition']}\n"
    
    prompt += """
    Please provide your valuation analysis in JSON format with the following structure:
    
    ```json
    {
      "new_value": 50000,
      "current_value_range": [15000, 20000],
      "confidence": "medium",
      "comparable_sales": [
        {
          "title": "2015 CAT D6 Dozer",
          "price": 35000,
          "url": "https://example.com/listing/123",
          "date": "2025-01-15"
        }
      ],
      "justification": "Detailed reasoning for the valuation...",
      "key_factors": ["Age impact", "Market trends", "Condition factors"]
    }
    ```
    
    Use web search to find comparable sales and current market values. Include specific sources for all information.
    """
    
    # Make API call with retry logic
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            message = client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4000,
                temperature=0,
                system="You are a heavy equipment valuation expert with access to web search. Provide structured JSON responses.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse the response
            result = parse_claude_response(message.content)
            
            # Save to cache
            save_to_cache(item_hash, result)
            
            return result
            
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt+1} failed: {str(e)}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"All attempts failed for {row['Unit #']}: {str(e)}")
                return {"error": str(e)}

def process_equipment_list(df, max_items=None):
    """
    Process multiple equipment items with progress tracking
    
    Args:
        df: DataFrame with equipment list
        max_items: Maximum number of items to process (None for all)
        
    Returns:
        Dictionary mapping unit IDs to valuation results
    """
    results = {}
    
    # Limit the number of items if specified
    process_df = df.head(max_items) if max_items else df
    
    for idx, row in tqdm(process_df.iterrows(), total=len(process_df), desc="Processing equipment"):
        unit_id = row['Unit #']
        result = process_equipment_item(row)
        results[unit_id] = result
        
        # Small delay to avoid API rate limits
        time.sleep(0.5)
        
    return results

def enhance_valuation(equipment_id, initial_valuation, row):
    """
    Add more depth to an existing valuation
    
    Args:
        equipment_id: Unit ID of the equipment
        initial_valuation: Initial valuation results
        row: DataFrame row with equipment details
        
    Returns:
        Enhanced valuation dictionary
    """
    prompt = f"""
    I have an initial valuation for this equipment:
    {json.dumps(initial_valuation, indent=2)}
    
    Please provide a more detailed analysis for:
    - Unit #: {row['Unit #']}
    - Description: {row['Description']}
    
    Focus on:
    1. Regional market variations for {row.get('Location', 'the region')}
    2. Recent auction results
    3. Maintenance history implications
    4. Parts availability impact on value
    5. Economic factors affecting this equipment category
    
    Provide the enhanced analysis in the same JSON format as the initial valuation, 
    but add an "enhanced_analysis" field with the additional details.
    """
    
    try:
        message = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=4000,
            temperature=0.1,  # Slightly higher temperature for more detail
            system="You are a heavy equipment valuation expert with access to web search. Provide enhanced analysis in the same JSON structure as the input, with an additional field for enhanced analysis.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Parse the response
        enhanced = parse_claude_response(message.content)
        
        # If the response was parsed as a complete new valuation
        if isinstance(enhanced, dict) and not enhanced.get("error"):
            # Ensure there's an enhanced_analysis field
            if "enhanced_analysis" not in enhanced:
                enhanced["enhanced_analysis"] = enhanced.get("justification", "")
            
            # Save enhanced valuation to cache with a different key
            item_hash = get_equipment_hash(row) + "_enhanced"
            save_to_cache(item_hash, enhanced)
            
            return enhanced
        else:
            return {"error": "Failed to enhance valuation"}
            
    except Exception as e:
        return {"error": str(e), "original_valuation": initial_valuation}