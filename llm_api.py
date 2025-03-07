import os
import json
import random
from typing import Dict, Any, List
from dotenv import load_dotenv
from phi.agent import Agent
from phi.model.google import Gemini
from config import CATEGORY_DETAILS, CORRECT_ANSWERS

# Load environment variables
load_dotenv()

# Get API key from environment
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in environment variables")

# Initialize Gemini agent with API key
agent = Agent(
    model=Gemini(api_key=api_key, id="gemini-2.0-flash"),
    markdown=True,
)

def shuffle_options(question: Dict) -> Dict:
    """Shuffle options while keeping track of the correct answer"""
    options = list(question["options"].items())
    correct_letter = question["correct"]
    correct_answer = question["options"][correct_letter]
    
    # Shuffle the options
    random.shuffle(options)
    
    # Create new options dictionary
    new_options = {}
    new_correct = None
    
    for i, (_, answer) in enumerate(options):
        letter = chr(97 + i)  # 'a', 'b', 'c', 'd'
        new_options[letter] = answer
        if answer == correct_answer:
            new_correct = letter
    
    # Update the question
    question["options"] = new_options
    question["correct"] = new_correct
    
    return question

def generate_questions(category: str) -> List[Dict]:
    try:
        category_info = CATEGORY_DETAILS[category]
        focus_areas = category_info["focus_areas"]
        
        prompt = f"""Generate 5 multiple-choice questions for assessing {category}.
        Category Description: {category_info['description']}
        Focus Areas: {', '.join(focus_areas)}

        Each question should:
        1. Test one of the focus areas mentioned above
        2. Present a realistic workplace scenario
        3. Have exactly 4 options labeled a, b, c, d
        4. Have exactly one correct answer
        5. Include an explanation for the correct answer

        Return the response in the following JSON format:
        [
            {{
                "question": "What would you do in this workplace scenario...?",
                "focus_area": "one of the focus areas",
                "options": {{
                    "a": "First option description",
                    "b": "Second option description",
                    "c": "Third option description",
                    "d": "Fourth option description"
                }},
                "correct": "a",
                "explanation": "Explanation why this is the correct answer"
            }}
        ]

        Ensure all options are properly labeled with lowercase letters (a, b, c, d) and the correct answer matches one of these letters.
        Return only the JSON array, no additional text or formatting.
        """

        # Get response from Gemini
        run = agent.run(prompt)
        content = run.content
        
        # Clean the response if needed
        content = content.replace("```json", "").replace("```", "").strip()
        
        try:
            # Parse the JSON response
            questions = json.loads(content)
            
            # Validate and shuffle each question
            shuffled_questions = []
            for i, q in enumerate(questions):
                # Validate question format
                required_keys = ["question", "options", "correct", "explanation"]
                if not all(key in q for key in required_keys):
                    raise ValueError(f"Question {i+1} is missing required keys")
                if not isinstance(q["options"], dict):
                    raise ValueError(f"Question {i+1} options is not a dictionary")
                if not all(key in q["options"] for key in ["a", "b", "c", "d"]):
                    raise ValueError(f"Question {i+1} is missing some options")
                
                # Shuffle options
                shuffled_q = shuffle_options(q.copy())
                shuffled_questions.append(shuffled_q)
                
                # Store correct answer
                CORRECT_ANSWERS[f"{category}_{i}"] = shuffled_q["correct"]
            
            return shuffled_questions
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Received content: {content}")
            return generate_default_questions(category)
            
    except Exception as e:
        print(f"Error in generate_questions: {str(e)}")
        return generate_default_questions(category)

def generate_default_questions(category: str) -> List[Dict]:
    """Generate default questions if API fails"""
    default_questions = []
    for i in range(5):
        question = {
            "question": f"Sample question {i+1} for {category}",
            "focus_area": CATEGORY_DETAILS[category]["focus_areas"][0],
            "options": {
                "a": "Option A",
                "b": "Option B",
                "c": "Option C",
                "d": "Option D"
            },
            "correct": "a",
            "explanation": "This is a default question due to API error."
        }
        shuffled_q = shuffle_options(question)
        default_questions.append(shuffled_q)
        CORRECT_ANSWERS[f"{category}_{i}"] = shuffled_q["correct"]
    
    return default_questions

def generate_report(scores: Dict[str, float], student_info: Dict[str, str]) -> str:
    try:
        avg_score = sum(scores.values()) / len(scores)
        strengths = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        improvements = sorted(scores.items(), key=lambda x: x[1])[:3]
        
        prompt = f"""
        Generate a detailed skill gap analysis report for:
        Name: {student_info['name']}
        Email: {student_info['email']}
        Department: {student_info['department']}
        Year: {student_info['year']}
        
        Overall Score: {avg_score:.1f}%
        
        Detailed Scores:
        {', '.join(f'{k}: {v:.1f}%' for k, v in scores.items())}
        
        Top Strengths:
        {', '.join(f'{k} ({v:.1f}%)' for k, v in strengths)}
        
        Areas for Improvement:
        {', '.join(f'{k} ({v:.1f}%)' for k, v in improvements)}
        
        Please provide:
        1. Executive summary
        2. Detailed analysis of each skill category
        3. Specific recommendations for improvement
        4. Suggested learning resources and next steps
        5. Career path recommendations based on strengths
        6. Action plan for next 3 months
        
        Format the response in markdown.
        """
        
        # Get response from Gemini
        run = agent.run(prompt)
        return run.content
        
    except Exception as e:
        return f"Error generating report: {str(e)}"
