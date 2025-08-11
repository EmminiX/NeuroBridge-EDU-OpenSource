"""
AI-powered summarization service using OpenAI GPT-4.1
Educational content summarization with async implementation
"""

import logging
from typing import Optional, Dict, Any
from openai import AsyncOpenAI
from .client import get_openai_client
from .prompts import EDUCATIONAL_SUMMARY_PROMPT, EDUCATIONAL_SUMMARY_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class SummarizationService:
    """
    AI-powered educational content summarization service
    
    Features:
    - GPT-4.1 model for high-quality summarization
    - Educational content optimization
    - Async implementation for performance
    - Error handling and retry logic
    - Customizable summarization parameters
    """
    
    def __init__(self):
        self.model = "gpt-4.1"  # Using GPT-4.1 with 1M token context window
        self.max_tokens = 1000
        self.temperature = 0.4  # Temperature for balanced creativity and consistency
    
    async def summarize_transcript(
        self,
        transcript: str,
        title: Optional[str] = None,
        context: Optional[str] = None,
        custom_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate educational summary from transcript
        
        Args:
            transcript: Raw transcript text to summarize
            title: Optional title/topic for context
            context: Optional additional context
            custom_instructions: Optional custom summarization instructions
            
        Returns:
            Dict containing summary, metadata, and processing info
            
        Raises:
            Exception: If summarization fails
        """
        try:
            client = await get_openai_client()
            
            # Build context-aware prompt
            user_prompt = self._build_user_prompt(
                transcript=transcript,
                title=title,
                context=context,
                custom_instructions=custom_instructions
            )
            
            # Generate summary using chat completions
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": EDUCATIONAL_SUMMARY_SYSTEM_PROMPT
                    },
                    {
                        "role": "user", 
                        "content": user_prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                presence_penalty=0.1,  # Slight penalty for repetition
                frequency_penalty=0.1   # Slight penalty for frequent tokens
            )
            
            # Extract summary content
            summary_content = response.choices[0].message.content.strip()
            
            # Calculate confidence score based on response
            confidence = self._calculate_confidence(response, transcript)
            
            result = {
                "summary": summary_content,
                "confidence": confidence,
                "model_used": self.model,
                "tokens_used": response.usage.total_tokens if response.usage else None,
                "processing_time": None,  # Could add timing if needed
                "metadata": {
                    "transcript_length": len(transcript),
                    "summary_length": len(summary_content),
                    "compression_ratio": len(summary_content) / len(transcript) if transcript else 0,
                    "title": title,
                    "context": context
                }
            }
            
            logger.info(f"Successfully generated summary using {self.model}")
            return result
            
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            raise Exception(f"Failed to generate summary: {str(e)}")
    
    async def summarize_transcript_stream(
        self,
        transcript: str,
        title: Optional[str] = None,
        context: Optional[str] = None,
        custom_instructions: Optional[str] = None
    ):
        """
        Generate educational summary from transcript with streaming
        
        Args:
            transcript: Raw transcript text to summarize
            title: Optional title/topic for context
            context: Optional additional context
            custom_instructions: Optional custom summarization instructions
            
        Yields:
            String chunks of the summary as they're generated
        """
        try:
            client = await get_openai_client()
            
            # Build context-aware prompt
            user_prompt = self._build_user_prompt(
                transcript=transcript,
                title=title,
                context=context,
                custom_instructions=custom_instructions
            )
            
            # Generate streaming summary using chat completions
            stream = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": EDUCATIONAL_SUMMARY_SYSTEM_PROMPT
                    },
                    {
                        "role": "user", 
                        "content": user_prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                presence_penalty=0.1,
                frequency_penalty=0.1,
                stream=True  # Enable streaming
            )
            
            # Yield chunks as they arrive
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            
            logger.info(f"Successfully streamed summary using {self.model}")
            
        except Exception as e:
            logger.error(f"Streaming summarization failed: {e}")
            raise Exception(f"Failed to stream summary: {str(e)}")
    
    async def generate_title(
        self,
        transcript_or_summary: str,
        max_length: int = 100
    ) -> str:
        """
        Generate a concise title for the content
        
        Args:
            transcript_or_summary: Content to generate title from
            max_length: Maximum title length
            
        Returns:
            Generated title string
        """
        try:
            client = await get_openai_client()
            
            prompt = f"""Generate a concise, educational title for this content. 
            The title should be informative and capture the main topic or theme.
            Maximum length: {max_length} characters.
            
            Content:
            {transcript_or_summary[:2000]}  # Truncate for efficiency
            
            Title:"""
            
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an educational content specialist. Generate clear, informative titles."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=50,
                temperature=0.5
            )
            
            title = response.choices[0].message.content.strip()
            
            # Ensure title length constraint
            if len(title) > max_length:
                title = title[:max_length-3] + "..."
            
            return title
            
        except Exception as e:
            logger.warning(f"Title generation failed: {e}")
            return "Educational Content Summary"  # Fallback title
    
    def _build_user_prompt(
        self,
        transcript: str,
        title: Optional[str] = None,
        context: Optional[str] = None,
        custom_instructions: Optional[str] = None
    ) -> str:
        """Build context-aware user prompt for summarization"""
        
        prompt_parts = [EDUCATIONAL_SUMMARY_PROMPT]
        
        if title:
            prompt_parts.append(f"\nTopic/Title: {title}")
        
        if context:
            prompt_parts.append(f"\nContext: {context}")
        
        if custom_instructions:
            prompt_parts.append(f"\nAdditional Instructions: {custom_instructions}")
        
        prompt_parts.append(f"\nTranscript to summarize:\n{transcript}")
        
        return "\n".join(prompt_parts)
    
    def _calculate_confidence(self, response, transcript: str) -> float:
        """
        Calculate confidence score for the summary
        
        Based on:
        - Response completion reason
        - Token usage efficiency  
        - Input quality indicators
        """
        try:
            base_confidence = 0.8
            
            # Check if response was truncated
            if response.choices[0].finish_reason == "length":
                base_confidence -= 0.2
            
            # Consider transcript length (very short or very long may be less reliable)
            transcript_length = len(transcript.split())
            if transcript_length < 50:  # Very short
                base_confidence -= 0.1
            elif transcript_length > 5000:  # Very long
                base_confidence -= 0.1
            
            # Token usage efficiency
            if response.usage:
                efficiency = response.usage.completion_tokens / response.usage.prompt_tokens
                if efficiency > 0.5:  # Very verbose response
                    base_confidence -= 0.1
                elif efficiency < 0.1:  # Very brief response
                    base_confidence -= 0.1
            
            return max(0.0, min(1.0, base_confidence))
            
        except Exception:
            return 0.7  # Default confidence


# Global service instance
summarization_service = SummarizationService()