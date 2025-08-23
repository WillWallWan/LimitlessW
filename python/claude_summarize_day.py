#!/usr/bin/env python3
"""
Claude-Powered Daily Summary

Uses Claude (Anthropic) to generate intelligent summaries of your daily conversations
from Limitless lifelogs.
"""

import os
from anthropic import Anthropic
from dotenv import load_dotenv
from _client import get_lifelogs

# Load environment variables
load_dotenv()

def summarize_with_claude(lifelogs, should_stream=True):
    """Summarize lifelogs using Claude"""
    
    # Get Claude API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Please set ANTHROPIC_API_KEY in your .env file")
        return
    
    # Initialize Claude client
    client = Anthropic(api_key=api_key)
    
    # Prepare conversation content
    conversation_text = ""
    for lifelog in lifelogs:
        conversation_text += f"\n--- {lifelog.get('title', 'Untitled')} ---\n"
        conversation_text += f"Time: {lifelog.get('startTime', 'Unknown')}\n"
        if lifelog.get('markdown'):
            conversation_text += lifelog['markdown'] + "\n\n"
    
    # Create the prompt
    prompt = f"""Please analyze these conversation transcripts from my day and provide:

1. **Executive Summary** - A brief overview of the day's key themes and activities
2. **Important Insights** - Key decisions, ideas, or realizations mentioned
3. **Action Items** - Tasks, commitments, or follow-ups that were discussed
4. **People & Relationships** - Important interactions and relationship updates
5. **Learning & Growth** - New knowledge, skills, or perspectives gained
6. **Mood & Energy** - Overall emotional tone and energy patterns

Conversation Transcripts:
{conversation_text}

Please be concise but insightful, focusing on what would be most valuable for personal reflection and productivity."""

    try:
        if should_stream:
            print("🤖 Claude is analyzing your conversations...\n")
            print("=" * 60)
            
            # Stream the response
            with client.messages.stream(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                for text in stream.text_stream:
                    print(text, end='', flush=True)
            
            print("\n" + "=" * 60)
            
        else:
            # Non-streaming response
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
            
    except Exception as e:
        print(f"❌ Error with Claude API: {e}")
        return None

def generate_action_insights(lifelogs):
    """Generate specific insights about action items and todos"""
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return
    
    client = Anthropic(api_key=api_key)
    
    # Prepare conversation content
    conversation_text = ""
    for lifelog in lifelogs:
        if lifelog.get('markdown'):
            conversation_text += lifelog['markdown'] + "\n\n"
    
    prompt = f"""Analyze these conversations and extract:

1. **Explicit Action Items** - Clear tasks mentioned ("I need to...", "I'll...")
2. **Implicit Commitments** - Unspoken obligations or expectations
3. **Deadlines & Timing** - When things need to be done
4. **Priority Assessment** - Which items seem most urgent/important
5. **Context & Dependencies** - What needs to happen first

Format as a clear, actionable list with urgency levels.

Conversations:
{conversation_text}"""

    try:
        print("\n🎯 **Detailed Action Item Analysis:**")
        print("=" * 50)
        
        with client.messages.stream(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                print(text, end='', flush=True)
        
        print("\n" + "=" * 50)
        
    except Exception as e:
        print(f"❌ Error generating action insights: {e}")

def main():
    """Main function to generate Claude-powered daily summary"""
    
    print("🤖 Claude-Powered Daily Summary")
    print("=" * 50)
    
    # Check API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Please add your Claude API key to .env file:")
        print("   ANTHROPIC_API_KEY=your_claude_key_here")
        return
    
    # Get Limitless API key
    limitless_key = os.getenv("LIMITLESS_API_KEY")
    if not limitless_key:
        print("❌ Please set LIMITLESS_API_KEY in your .env file")
        return
    
    print("📚 Fetching your recent conversations...")
    
    try:
        # Get today's conversations (or recent ones)
        lifelogs = get_lifelogs(
            api_key=limitless_key,
            limit=20,  # Adjust based on how much data you want to analyze
            direction="desc",
            includeMarkdown=True
        )
        
        if not lifelogs:
            print("📭 No conversations found!")
            return
        
        print(f"✅ Found {len(lifelogs)} conversations to analyze")
        
        # Generate summary
        summarize_with_claude(lifelogs, should_stream=True)
        
        # Generate detailed action insights
        generate_action_insights(lifelogs)
        
        print("\n💡 **Tips:**")
        print("- Run this daily for best insights")
        print("- Combine with the todo calendar for action items")
        print("- Use different limits (5, 20, 50) for different depth")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()


