#!/usr/bin/env python3
"""
Daily Summary Generator

Creates a comprehensive summary of your day based on conversation transcripts.
Focuses on key meetings, learnings, decisions, problems/solutions, and themes
in chronological order for daily review.
"""

import os
import time
from datetime import datetime, timedelta
from anthropic import Anthropic
from dotenv import load_dotenv
from _client import get_lifelogs

# Load environment variables
load_dotenv()

def summarize_day_batch(lifelogs_batch, batch_num):
    """Use Claude to create a day summary from a batch of conversations"""
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Please set ANTHROPIC_API_KEY in your .env file")
        return []
    
    client = Anthropic(api_key=api_key)
    
    # Prepare batch content
    conversation_content = ""
    
    for i, lifelog in enumerate(lifelogs_batch, 1):
        title = lifelog.get('title', f'Conversation {i}')
        start_time = lifelog.get('startTime', 'Unknown')
        markdown = lifelog.get('markdown', '')
        
        # Keep more content than todo extraction to see full conversations
        if len(markdown) > 1200:
            markdown = markdown[:1200] + "... [truncated for analysis]"
        
        # Format time nicely
        time_str = "Unknown"
        if start_time != 'Unknown':
            try:
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                time_str = dt.strftime("%I:%M %p")
            except:
                time_str = start_time[:5]
        
        conversation_content += f"\n=== {i}. {title} ({time_str}) ===\n{markdown}\n"
    
    # User's excellent day summary prompt
    prompt = f"""I need a summary of my day based on my conversation transcripts from yesterday. Look at the transcript and respond with a summary of my day that I can use to review everything that happened quickly.

Here are the things I want to be included in the summary:
- Key meetings and conversations I participated in
- Important information I learned or shared
- Decisions I made or was involved in
- Problems I encountered and solutions I found
- Major themes or patterns in my conversations

Format the summary to be readable and insightful, highlighting what matters most about my day. Keep it brief but comprehensive, capturing the essence of my experiences rather than listing every detail.

Show me the summary in chronological order when possible, starting with morning activities and ending with evening ones. Prioritize significant events over routine interactions.

Conversation Transcripts:
{conversation_content}

Please provide a comprehensive day summary based on these conversation transcripts:"""

    try:
        print(f"🤖 Creating day summary for batch {batch_num}...")
        
        # Use the better model for this analysis
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",  # Better model for nuanced analysis
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = message.content[0].text
        
        if response_text and len(response_text.strip()) > 20:
            print(f"✅ Batch {batch_num}: Day summary created!")
            return response_text
        else:
            print(f"📭 Batch {batch_num}: No significant activity found")
            return None
            
    except Exception as e:
        print(f"❌ Batch {batch_num} error: {e}")
        return None

def create_yesterday_summary():
    """Create a comprehensive summary of yesterday's conversations"""
    
    # Calculate yesterday
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    yesterday_str = yesterday.strftime("%Y-%m-%d")
    
    print("📋 Daily Summary - Yesterday's Conversations")
    print("=" * 60)
    print(f"🗓️  Analyzing: {yesterday_str}")
    
    # Check API keys
    limitless_key = os.getenv("LIMITLESS_API_KEY")
    claude_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not limitless_key or not claude_key:
        print("❌ Please ensure both API keys are set in .env file")
        return
    
    print(f"\n📚 Fetching conversations...")
    
    try:
        # Get conversations
        lifelogs = get_lifelogs(
            api_key=limitless_key,
            date=yesterday_str,
            includeMarkdown=True,
            direction="asc"
        )
        
        if not lifelogs:
            print(f"📭 No conversations found for {yesterday_str}")
            return
        
        print(f"✅ Found {len(lifelogs)} conversations")
        print(f"🔄 Processing for daily summary...")
        
        # Process in batches (larger batches since we're not being as strict)
        batch_size = 5  # Slightly larger batches for better context
        all_insights = []
        
        for i in range(0, len(lifelogs), batch_size):
            batch = lifelogs[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            
            print(f"\n📦 Processing batch {batch_num} ({len(batch)} conversations)...")
            
            # Show what's in this batch
            for j, lifelog in enumerate(batch, 1):
                title = lifelog.get('title', 'Untitled')
                start_time = lifelog.get('startTime', 'Unknown')
                time_str = "Unknown"
                if start_time != 'Unknown':
                    try:
                        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        time_str = dt.strftime("%I:%M %p")
                    except:
                        pass
                print(f"   {j}. {time_str} - {title[:50]}...")
            
            # Create day summary for this batch
            insights = summarize_day_batch(batch, batch_num)
            if insights:
                all_insights.append({
                    'batch_num': batch_num,
                    'content': insights,
                    'conversations': [lifelog.get('title', 'Untitled') for lifelog in batch]
                })
            
            # Rate limiting delay
            if i + batch_size < len(lifelogs):  # Not the last batch
                print("⏳ Waiting 3 seconds...")
                time.sleep(3)
        
        # Display results
        print(f"\n🎉 Analysis Complete!")
        print("=" * 60)
        
        if not all_insights:
            print("📭 No significant activity found across all conversations")
            print("\n🤔 This could mean:")
            print("   • Conversations were mostly routine/casual")
            print("   • You had a quiet day (which is totally fine!)")
            print("   • Day was more listening/observing than participating")
            return
        
        print(f"✨ Created day summary from {len(all_insights)} out of {batch_num} batches")
        
        for insight in all_insights:
            print(f"\n📅 **TIME PERIOD {insight['batch_num']} - DAY SUMMARY:**")
            print("-" * 60)
            print(insight['content'])
            print(f"\nConversations included: {', '.join(insight['conversations'][:3])}{'...' if len(insight['conversations']) > 3 else ''}")
            print()
        
        # Summary
        print(f"📊 **Summary:**")
        print("-" * 30)
        print(f"   • {len(lifelogs)} conversations analyzed")
        print(f"   • {len(all_insights)} time periods with significant activity")
        print(f"   • Daily summary completeness: {'Comprehensive' if all_insights else 'Limited'}")
        
        if all_insights:
            print(f"\n💡 **Daily Review Value:**")
            print(f"   • Comprehensive overview of your day's activities")
            print(f"   • Key learnings and decisions captured") 
            print(f"   • Major themes and patterns identified")
            print(f"   • Perfect for reflection and follow-up planning")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    create_yesterday_summary()
