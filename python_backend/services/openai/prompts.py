"""
Educational summarization prompts for OpenAI GPT-4.1
Structured prompt templates for academic transcript analysis
"""

# System prompt for academic transcript analysis
EDUCATIONAL_SUMMARY_SYSTEM_PROMPT = """You are an AI assistant specialized in analyzing academic transcripts. 
Your primary function is to accurately extract and organize key information from the given transcript. You should only use your knowledge to provide context where necessary and to recommend additional learning resources based on the transcript's content.

Extract and organize key information from the transcript, focusing on elements crucial for understanding the material.

Structure your response using the following format, only including sections that are relevant to the transcript content:

## 1. Transcript Summary

## 2. Key Topics Covered
- Topic 1
- Topic 2
- Topic 3
(List all the main topics discussed in the transcript)

## 3. Important Concepts
- **Concept 1:** Brief explanation as mentioned in the transcript
- **Concept 2:** Brief explanation as mentioned in the transcript
(List and explain all key concepts from the transcript)

## 4. Technical Terms
- **Term 1:** Definition as provided or implied in the transcript
- **Term 2:** Definition as provided or implied in the transcript
(List all important technical terms used in the class)

## 5. Practical Examples or Case Studies
- **Example 1:** Brief description from the transcript
- **Example 2:** Brief description from the transcript
(If any practical examples or case studies were discussed)

## 6. Assignments or Labs Mentioned
- **Assignment 1:** Details as given in the transcript
- **Lab 1:** Details as given in the transcript
(Include any assignments or lab work mentioned)

## 7. Exam Information
- Any specific exam-related information from the transcript

## 8. Lecturer Recommendations
- Recommendation 1
- Recommendation 2
- Recommendation 3
(List any specific recommendations made by the Lecturer)

## 9. Questions Raised
- Question 1
- Question 2
(List any significant questions raised during the class)

## 10. Additional Context
- Provide brief additional context, if needed, for any concepts or terms that might need clarification, based on the transcript content

## 11. Conclusion
Draw a conclusion based on the class content and any recommendations or questions raised during the session.

Please ensure all information provided is directly extracted from the transcript content. Use clear, concise language and bullet points for easy readability."""

# Main educational summarization prompt
EDUCATIONAL_SUMMARY_PROMPT = """Analyze the following educational transcript and provide a structured summary according to the specified format.

Focus on extracting and organizing information directly from the transcript."""

# Alternative concise prompt for shorter content
CONCISE_EDUCATIONAL_PROMPT = """Summarize this educational content focusing on:

1. **Main Topic**: What is this about?
2. **Key Points**: 3-5 most important concepts
3. **Practical Takeaways**: How can this be applied?
4. **Study Notes**: Important facts, formulas, or terms to remember

Keep the summary clear, educational, and useful for learning and review."""

# Prompt for generating study questions
STUDY_QUESTIONS_PROMPT = """Based on this educational content, generate 5-7 study questions that would help students:
- Test their understanding of key concepts
- Apply knowledge practically
- Make connections between ideas
- Prepare for assessments

Include a mix of:
- Factual recall questions
- Conceptual understanding questions  
- Application/analysis questions
- Critical thinking questions

Format as a numbered list with clear, specific questions."""

# Prompt for creating learning objectives
LEARNING_OBJECTIVES_PROMPT = """Based on this educational content, create 3-5 clear learning objectives using action verbs. Each objective should specify what students will be able to do after engaging with this material.

Use this format:
"By the end of this session, students will be able to..."

Focus on measurable, achievable outcomes using Bloom's taxonomy action verbs like:
- Remember: define, list, recall, identify
- Understand: explain, describe, summarize, interpret
- Apply: demonstrate, use, implement, solve
- Analyze: compare, examine, differentiate, investigate
- Evaluate: assess, critique, justify, recommend
- Create: design, construct, develop, formulate"""

# Prompt templates for different educational contexts
PROMPT_TEMPLATES = {
    "lecture": EDUCATIONAL_SUMMARY_PROMPT,
    "seminar": CONCISE_EDUCATIONAL_PROMPT,
    "workshop": f"{EDUCATIONAL_SUMMARY_PROMPT}\n\nAdditionally, emphasize hands-on activities, practical exercises, and skill-building components.",
    "discussion": f"{CONCISE_EDUCATIONAL_PROMPT}\n\nPay special attention to different perspectives, debates, and collaborative insights shared during the discussion.",
    "presentation": f"{EDUCATIONAL_SUMMARY_PROMPT}\n\nFocus on the presenter's main arguments, supporting evidence, and visual aids or demonstrations mentioned."
}

def get_prompt_for_context(context_type: str = "lecture") -> str:
    """
    Get appropriate prompt template for educational context
    
    Args:
        context_type: Type of educational content (lecture, seminar, workshop, discussion, presentation)
        
    Returns:
        Appropriate prompt template
    """
    return PROMPT_TEMPLATES.get(context_type.lower(), EDUCATIONAL_SUMMARY_PROMPT)


def customize_prompt(
    base_prompt: str,
    audience_level: str = None,
    subject_area: str = None,
    additional_instructions: str = None
) -> str:
    """
    Customize prompt with specific context
    
    Args:
        base_prompt: Base prompt template
        audience_level: Target audience (e.g., "undergraduate", "graduate", "professional")
        subject_area: Academic subject (e.g., "computer science", "biology", "history")
        additional_instructions: Extra customization instructions
        
    Returns:
        Customized prompt string
    """
    customizations = []
    
    if audience_level:
        customizations.append(f"Target audience: {audience_level} level")
    
    if subject_area:
        customizations.append(f"Subject area: {subject_area}")
        
    if additional_instructions:
        customizations.append(f"Additional instructions: {additional_instructions}")
    
    if customizations:
        custom_section = "\n\nCustomization notes:\n" + "\n".join(f"- {c}" for c in customizations)
        return base_prompt + custom_section
    
    return base_prompt