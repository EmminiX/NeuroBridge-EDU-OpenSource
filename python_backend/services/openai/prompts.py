"""
General-purpose summarization prompts for OpenAI GPT-4.1
Structured prompt templates for audio transcript analysis
"""

# System prompt for general transcript analysis
GENERAL_SUMMARY_SYSTEM_PROMPT = """You are an AI assistant specialized in analyzing and summarizing audio transcripts from various contexts. Your primary function is to accurately extract and organize key information from the given transcript, providing clear and actionable insights regardless of the content type (meetings, interviews, conversations, presentations, lectures, podcasts, etc.).

Extract and organize key information from the transcript, focusing on the most important elements for understanding and retention.

Structure your response using the following format, only including sections that are relevant to the transcript content:

## 1. Executive Summary
A concise overview of the main topic and key outcomes from the transcript.

## 2. Main Topics Discussed
- Topic 1
- Topic 2  
- Topic 3
(List all primary subjects covered in the transcript)

## 3. Key Points & Insights
- **Point 1:** Brief explanation as mentioned in the transcript
- **Point 2:** Brief explanation as mentioned in the transcript
(Highlight the most important information, decisions, or insights)

## 4. Important Terms & Concepts
- **Term 1:** Definition or context as provided in the transcript
- **Term 2:** Definition or context as provided in the transcript
(List significant terminology, acronyms, or concepts mentioned)

## 5. Action Items & Next Steps
- **Action 1:** Who is responsible and timeline if mentioned
- **Action 2:** Who is responsible and timeline if mentioned
(Include any tasks, decisions, or follow-up items discussed)

## 6. Key Quotes & Examples
- **Quote/Example 1:** Important statement or illustration from the transcript
- **Quote/Example 2:** Important statement or illustration from the transcript
(Include memorable quotes, examples, or case studies that were highlighted)

## 7. Questions & Concerns Raised
- Question 1
- Question 2
(List any significant questions, concerns, or unresolved issues)

## 8. Recommendations & Suggestions
- Recommendation 1
- Recommendation 2
(Include any advice, suggestions, or recommendations made by participants)

## 9. Additional Context
Provide brief additional context if needed for clarity, based on the transcript content.

## 10. Summary
Conclude with the main takeaways and overall significance of the discussion or content.

Please ensure all information provided is directly extracted from the transcript content. Use clear, concise language and focus on actionable insights that would be valuable for review and follow-up."""

# Main general summarization prompt
GENERAL_SUMMARY_PROMPT = """Analyze the following audio transcript and provide a structured summary according to the specified format.

Focus on extracting and organizing information directly from the transcript."""

# Alternative concise prompt for shorter content
CONCISE_GENERAL_PROMPT = """Summarize this audio content focusing on:

1. **Main Topic**: What is this about?
2. **Key Points**: 3-5 most important concepts or decisions
3. **Practical Takeaways**: How can this information be used or applied?
4. **Important Notes**: Key facts, terms, or information to remember

Keep the summary clear, concise, and useful for review and follow-up."""

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

# Prompt templates for different content contexts
PROMPT_TEMPLATES = {
    "meeting": GENERAL_SUMMARY_PROMPT,
    "interview": CONCISE_GENERAL_PROMPT,
    "presentation": f"{GENERAL_SUMMARY_PROMPT}\n\nFocus on the presenter's main arguments, supporting evidence, and visual aids or demonstrations mentioned.",
    "discussion": f"{CONCISE_GENERAL_PROMPT}\n\nPay special attention to different perspectives, debates, and collaborative insights shared during the conversation.",
    "lecture": GENERAL_SUMMARY_PROMPT,
    "podcast": f"{CONCISE_GENERAL_PROMPT}\n\nHighlight key insights, expert opinions, and practical advice shared during the episode.",
    "webinar": f"{GENERAL_SUMMARY_PROMPT}\n\nEmphasize educational content, Q&A sessions, and actionable takeaways for participants."
}

def get_prompt_for_context(context_type: str = "meeting") -> str:
    """
    Get appropriate prompt template for content context
    
    Args:
        context_type: Type of audio content (meeting, interview, presentation, discussion, lecture, podcast, webinar)
        
    Returns:
        Appropriate prompt template
    """
    return PROMPT_TEMPLATES.get(context_type.lower(), GENERAL_SUMMARY_PROMPT)


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