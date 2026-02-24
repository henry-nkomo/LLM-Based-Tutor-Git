import math
from typing import Any, List, get_origin
from flask import session
from .state import mainState, generalChat, DiagnosisQueries
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langchain_pinecone.vectorstores import Pinecone, PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from project_files.add_retrieve_data import retrieveData
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from google.api_core.exceptions import ResourceExhausted
from pydantic import ValidationError, Field
import re, json
from dotenv import load_dotenv
import os
import random

embeddings = OpenAIEmbeddings(model="text-embedding-3-small", dimensions=768)
skill_components = retrieveData()
progress = retrieveData()

load_dotenv()
O_api_key = os.getenv("OPENAI_API_KEY")

print(O_api_key)

# Initialize the LLM
llm = ChatOpenAI(
    model="gpt-5-2025-08-07",  # you can replace with "gpt-4" or others
    api_key=O_api_key,
    temperature=1
)

"""google_gen_ai = os.getenv('GOOGLE_API_KEY')
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite", api_key=google_gen_ai)
"""
# Load Claude API key from environment variable
A_api_key = os.getenv("ANTHROPIC_API_KEY")

# Initialize Claude (Sonnet in this case)
"""llm = ChatAnthropic(
    model="claude-3-haiku-20240307",  # haiku / sonnet / opus are available
    temperature=0,
    api_key=A_api_key
)"""

embeddings = OpenAIEmbeddings(model="text-embedding-3-small", dimensions=768)

##################################################################
############  graph for tutoring
##################################################################
def ocherstrator_node(state: mainState) -> mainState:
    print("-------ocherstrator node")
    if len(state.history) > 20:
        summary_list = list(state.history.items())
        new_summary_list = summary_list[20:30]

        try:
            template = """
                You  are an expert at summarising and following instructions

                context:
                    dialogue to summarise: {summary_dialogue} 

                instructions:
                    1. Summarise the dialogue in a sentence, capture the student's weakness, strengths and what you recomend on them to
                      improve their learning trajectory of English comprehension.
            """
            prompt = ChatPromptTemplate.from_template(template)
            chain = prompt | llm | StrOutputParser()
            summary_report = chain.invoke({"summary_dialogue": new_summary_list})

            progress.update_report_summary(state.user_id, summary_report)
        except ResourceExhausted as e:
            state.ai_response = "An error occured"
            return state
    return state 

def ocherstrator_edge(state: mainState) -> mainState:
    print("the current state is **/")
    """This function routes to the correct pathway for handling a task delegation"""
    if state.current_state == "preamble" or state.current_state == "no_question":
        print("Routing to preamble...")
        return "preamble"
    if state.current_state == "question":
        print("Routing to question generator...")
        return "question_generator"
    if state.current_state == "assessment":
        print("Routing to assessor...")
        return "assessor"
    else: #general message
        print("Routing to dialogue manager...")
        return "dialogue_manager" 
    
def preamble_node(state: mainState) -> mainState:
    """This function serves to introduce the student when the tutoring session which is just starting"""
    print("------------preamble node")
    try:
        template = """
            You are an expert Tutor who possesses people skills. 

            context:
              Student's name: {username}
              Student's message: {user_message}
              Chat history: {history}

            instructions:
              1. You are about to begin an English comprehension tutoring session with the student what they shoud focus on is 
                 determined by the system just focus on greeting them asking if they are ready for the tutoring session.
              2. Look at the chat history:
                 - If empty or very short (1-2 exchanges), greet the student warmly and ask how they're feeling about starting the session.
                 - Continue building rapport and don't rush to start the exercises.
              3. Continue the dialogue and assess if the student is ready for a tutoring session, your approach is of someone who wants to start the tutoring session.
              4. IMPORTANT: Only mark the student as "ready" if they EXPLICITLY indicate readiness with phrases like:
                 - "I'm ready"
                 - "Let's start"
                 - "Yes, I want to begin"
                 - "Let's do this"
                 - Similar clear affirmations
              5. Your responses should be short and precise.
              6. If the student is ready mark current state as "question" an tell them you will send a question with instructions shortly, otherwise "no_question".
              7. Respond ONLY in JSON format {{"current_state": "<question_status>", "ai_response": "<your message>"}}
        """
        prompt = ChatPromptTemplate.from_template(template)
        retrieval_chain = (
        {"user_message": lambda x: state.user_message, "history": lambda x: state.history, "username": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
        )
        response = retrieval_chain.invoke(state.username)
        response_sanitised = re.sub(r"```json\s*|\s*```", "", response.strip())

        print("--------", response_sanitised)

        try:
            data = json.loads(response_sanitised)
            temporary_state = mainState(**data)

            for field_name in state.model_fields:
                new_value = getattr(temporary_state , field_name)

                if new_value is not None:
                    setattr(state, field_name, new_value)
            return state
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"Failed to parse or validate LLM output: {e}")
    except ResourceExhausted as e:
        state.ai_response = "An error occured"
        return state

def general_node(state: mainState) -> mainState:
    """This function serves to manage chat which has went off topic, these are messages from the student 
       which do not necessarily answer the question posed by the tutor"""
    print("----------------general_node")
    try:
        template = """
            You are a friendly and engaging tutor. Your role is to maintain a positive and supportive conversation with the student.
            
            context:
                Student's name: {username}
                Student's message: {user_message}
                Chat history: {history}

            instructions:
                1. A conversation has went off topic, engage in a friendly and supportive manner and respond to the student.
                2. While responding nudge/ steer the conversation back on track and encourage the student to answer a question if the was a question asked earlier.
        """
        prompt = ChatPromptTemplate.from_template(template)
        retrieval_chain = (
        {"user_message": lambda x: state.user_message, "history": lambda x: state.history, "username": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
        )
        response = retrieval_chain.invoke(state.username)
        state.ai_response = response
        return state
    except ResourceExhausted as e:
        state.ai_response = "An error occured while managing the chat."
        return state

def question_generator(state: mainState) -> mainState:
    """This funtion generates questions"""
    print("Question generator node.........")
    ranges = {'first': [],'second': [],'third': [],'fourth': [],'fifth': []}

    for K_component, level in state.skill_component.items():
        if level <= 20:
            ranges['first'].append(K_component)
        elif 21 <= level <=40:
            ranges['second'].append(K_component)
        elif 41 <= level <=60:
            ranges['third'].append(K_component) 
        elif 61 <= level <=80:  
            ranges['fourth'].append(K_component)
        else:
            ranges['fifth'].append(K_component)

    while True:

        random_num = random.randint(1,20)
        #for 40% of the time generate questions that target a learner's weak skill
        if random_num <= 10:
            if ranges['first']:
                components = list(ranges['first'])
                target_comp = components[random.randint(0, len(components)-1)]
                break
        elif 11 <= random_num <=14:
            if ranges['second']:
                components = list(ranges['second'])
                target_comp = components[random.randint(0, len(components)-1)]     
                break 
        elif 15 <= random_num <=17:
            if ranges['third']:
                components = list(ranges['third'])
                target_comp = components[random.randint(0, len(components)-1)]
                break
        elif 18 <= random_num <=19:
            if ranges['fourth']:
                components = list(ranges['fourth'])
                target_comp = components[random.randint(0, len(components)-1)]
                break
        else:
            if ranges['fifth']: 
                components = list(ranges['fifth'])
                target_comp = components[random.randint(0, len(components)-1)]
                break
    
    comprehending_text = ["comprehending text", "understanding explicit information", "making inferences", "identifying main ideas and supporting details", "understanding purpose and context"]
    vocabulary = ["vocabulary", "understanding word meanings", "using context clues", "understanding figurative language", "understanding word relationships"]
    summarisation = ["summarization", "identifying key points", "producing summaries in own words"]  

    if target_comp == "comprehending-text":
        query = random.choice(comprehending_text)
    elif target_comp == "vocabulary":
        query = random.choice(vocabulary)
    elif target_comp == "summarisation":
        query = random.choice(summarisation)
    state.target_skill = target_comp

    vectorstore = PineconeVectorStore(index_name="past-papers-index", embedding=embeddings)

    retrieved_docs = vectorstore.similarity_search(query, k=5)

    weights = [0.40, 0.25, 0.18, 0.10, 0.07]  
    selected_doc = random.choices(retrieved_docs, weights=weights[:len(retrieved_docs)], k=1)[0]

    try:
        template = """
            You are an expert grade 12 level English comprehension question generator.

            context:
                Target skill component: {skill_component}
                Retrieved document: {selected_doc}

            instructions:
                1. Skill components are defined as follows:
                    - comprehending-text: understanding explicit information, making inferences, 
                        identifying main ideas and supporting details, understanding purpose and context
                    - vocabulary: understanding word meanings, using context clues, understanding 
                        figurative language, understanding word relationships
                    - summarization: identifying key points, producing summaries in own words
                2. Use the retrieved document to generate ONE grade 12 level question targeting 
                the skill component provided. Do NOT mention the skill component by name.
                3. Your response MUST follow this EXACT structure with no deviation:
                    PASSAGE:
                    [Copy 1-2 paragraphs verbatim from the retrieved document here]

                    QUESTION:
                    [Write your question here - this field MUST NOT be empty]
                4. The question MUST:
                    - Be directly answerable from the passage above
                    - Be appropriate for grade 12 level complexity
                    - Target the skill component without naming it
                IMPORTANT: You MUST include both the PASSAGE and QUESTION sections. 
                A response without a QUESTION is invalid.
        """

        prompt = ChatPromptTemplate.from_template(template)

        chain = prompt | llm | StrOutputParser()

        result = chain.invoke({
            "skill_component": target_comp,
            "selected_doc": selected_doc
        })

        print("question generator response***************", result)
        
        response_sanitised = re.sub(r"```json\s*|\s*```", "", result.strip())
        response_sanitised = response_sanitised.replace('"', '"').replace('"', '"').replace("'", "'").replace("'", "'")
        #print("-------------we at question generator", response_sanitised)

        """# EXTRACT ONLY THE JSON PART
        json_match = re.search(r'\{.*?\}', response_sanitised, re.DOTALL)
        if not json_match:
            print("No JSON found in response")
            state.ai_response = "Error generating question."
            state.status = "no_question"
            return state

        json_str = json_match.group(0)

        print("--------danzo1111  state value....")
        
        saved_target_skill = state.target_skill
        saved_skill_component = state.skill_component
    
        try:
            data = json.loads(json_str)  # Parse the extracted JSON only
            
            # Update only fields from JSON
            for field_name, field_value in data.items():
                if hasattr(state, field_name):
                    setattr(state, field_name, field_value)
            
            state.current_question = state.ai_response
            if not state.target_skill:
                state.target_skill = saved_target_skill
            if not state.skill_component:
                state.skill_component = saved_skill_component
            return state
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"Failed to parse or validate LLM output: {e}")
            return state"""
        
        state.ai_response = result
        state.current_state = "assessment"
        state.current_question = result

        return state

    except Exception as e:
        print("///Error in generating question", e)
        return state

def assessor(state: mainState) -> mainState:
    print("Assessor node.........")
    print("--------danzo  state value....", state.target_skill)
    try:
        template = """
            You are a warm, patient English tutor having a real conversation with a student. 
            You genuinely care about their progress and speak naturally, not like a marking machine.
            You assess a student's response and guide them with a teaching philosophy 
            that centers on clear, Socratic questioning, scaffolding to achieve the Zone of Proximal Development. 
            You do not give the student the direct answer but guide them to get it on their own through conversation.

            context:
                Student's name: {username}
                Student's answer: {user_message}
                Question asked: {question}
                Number of attempts made by the student: {attempts}
                Conversation history: {history}

            instructions:
                1. Look at the student's  answer and READ the conversation history and notice any patterns between the answer and conversation history
                   not to lecture the student, but to connect the dots naturally in conversation. For example, instead of 
                "I notice you have a recurring weakness in inference", say something like 
                "You know, I'm seeing something similar to what came up earlier - you're picking 
                up the surface detail but the deeper meaning is slipping through."
                Recurring mistakes or weaknesses the student has shown across multiple questions, might include:
                    - Repeatedly missing implicit meaning or inference
                    - Consistently poor grammar or sentence structure  
                    - Struggling to use their own words (copying verbatim)
                    - Missing key points in summaries
                    - Misunderstanding vocabulary in context


                2. RESPOND like a real tutor would in a one-on-one session:
                - Acknowledge what they said first before evaluating it
                - If they're on the right track, say so genuinely before pointing out what's missing
                - If they're off track, don't just say "wrong" - respond to the specific thing 
                    they said and redirect naturally
                - Use the student's name occasionally to keep it personal

                3. If it is the student's first, second, third or fourth attempt:
                - Mark the answer out of 3:
                    * 3 marks: fully correct
                    * 1 mark: partially correct  
                    * 0 marks: completely wrong
                - If correct: state feedback as "correct" and affirm them.
                - If partially correct or wrong: state feedback as "wrong", encourage them 
                    to try again, and provide a Socratic hints without giving the answer away.
                - If a recurring weakness was identified in step 1, EXPLICITLY mention it.
                respond ONLY in JSON format {{"feedback": "correct" or "wrong", "mark": <marks_awarded>, "ai_response": "<your response>"}}.


                4. HINTS should feel like conversation, not clues in a game:
                - Bad: "Think about what the author implies rather than states explicitly."
                - Good: "Okay so you've picked up that the farmer uses compost - good. 
                    But why do you think the passage mentions animals roaming freely right 
                    after that? What's the connection the writer is making?"

                5. ATTEMPT 5 (final attempt): 
                - Be honest but kind - "Okay, let me show you how I'd approach this..."
                - Walk through the reasoning like you're thinking aloud together
                - End with something forward-looking: "Now that you've seen how that works, 
                    watch out for this pattern in the next one."

                6. GRAMMAR: If you spot grammar issues in their response, weave the correction 
                naturally into your reply rather than listing it separately. 
                For example: "I like what you're going for - and just a small thing, 
                it would be 'allows the environment to recover' not 'allow'."

                7. Keep responses SHORT - 3 to 5 sentences max. You're having a conversation, 
                not writing a report.

                Respond ONLY in JSON format:
                {{"feedback": "correct" or "wrong", "mark": <number or null>, "ai_response": ""}}
                REMEMBER DO NOT  GIVE OUT THE ANSWERS  BUT GUIDE THE STUDENT TO GET IT ON THEIR OWN THROUGH CONVERSATION.
        """
        prompt = ChatPromptTemplate.from_template(template)
        retrieval_chain = (
            {
                "user_message": lambda x: state.user_message,
                "question": lambda x: state.current_question,
                "attempts": lambda x: state.attempts,
                "history": lambda x: state.history,    
                "username": RunnablePassthrough()
            }
            | prompt
            | llm
            | StrOutputParser()
        )
        response = retrieval_chain.invoke(state.username)
        response_sanitised = re.sub(r"```json\s*|\s*```", "", response.strip())

        print("--------question assessor response***************", state.current_question)
        print("--------attempts***************", state.attempts)

        try:
            data = json.loads(response_sanitised)
            
            # Only update fields that were actually returned by the LLM
            for field_name, field_value in data.items():
                if hasattr(state, field_name):
                    setattr(state, field_name, field_value)

            # Now handle logic based on feedback
            if state.feedback == "correct":
                # Update knowledge state on ANY correct answer (even if not first attempt)
                if state.attempts == 0:  # Only update on first attempt of THIS question
                    knowledgeStateData = skill_components.get_skill_components(session['user_id'])
                    print("First attempt correct answer - updating skill components")
                    print("Skill components before update:", knowledgeStateData)
                    
                    feedback_state = state.mark if state.mark else 3  # default to 3 if missing
                    mastery_estimate = knowledgeStateData.get(state.target_skill, 0)
                    expected_value = 1 / (1 + math.exp(-mastery_estimate))
                    
                    new_value = mastery_estimate + (feedback_state - expected_value) * 0.1
                    knowledgeStateData[state.target_skill] = new_value
                    skill_components.update_skill_components(session['user_id'], knowledgeStateData)
                    
                    print("Updated skill components:", knowledgeStateData)
                
                state.current_state = "question"
                state.status = "question"
                state.attempts = 0  # Reset for new question

            elif state.feedback == "wrong":
                print("-------attempts before increment", state.attempts)
                state.attempts += 1
                print("-------attempts after increment", state.attempts)
                state.current_state = "assessment"
            else:
                # Safety: if feedback is neither correct nor wrong, something went wrong
                print(f"ERROR: Unexpected feedback value: {state.feedback}")
                state.current_state = "assessment"
                
            return state
            
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"Failed to parse or validate LLM output: {e}")
            return state

    except ResourceExhausted as e:
        state.ai_response = "Exhausted resources for the day try again after 24 hours"
        return state
    
def assessor_edge(state: mainState) ->mainState:
    """This function routes to the correct pathway after the assessor node"""
    if state.feedback == "correct":
        state.current_state = "question"
        return "question_generator"
    else:
        state.current_state = "assessment"
        return "assessor"
         
def tutor_graph():
    """This function compiles and returns the tutoring graph"""

    graph = StateGraph(mainState)
    graph.add_node("start", ocherstrator_node)
    graph.add_node("question_generator", question_generator)
    graph.add_node("assessor", assessor)
    graph.add_node("preamble", preamble_node)
    graph.add_node("general_manager", general_node)

    graph.set_entry_point("start")

    graph.add_conditional_edges(
        "start",
        ocherstrator_edge,
        {
            "preamble": "preamble",
            "assessor": "assessor",
            "question_generator": "question_generator",
            "dialogue_manager": "general_manager"
        }
    )

    graph.add_conditional_edges(
        "assessor",
        assessor_edge,
        {
            "question_generator": "question_generator",
            "assessor": END
        }
    )

    graph.add_edge("question_generator", END)
    graph.add_edge("preamble", END)
    graph.add_edge("general_manager", END)
    return graph.compile()



@tool
def initialise_dashboard_chat(
    username: str, 
    history: str = Field(default="", description="Previous conversation history as a string")
) -> str:
    """This function sends the initial conversation message by greeting the user
    
    Args:
        username: The name of the student
        history: Previous conversation history as a string (optional, defaults to empty string)
    """
    print("-------initialise dashboard chat tool called with username:", username)
    print(f"       History provided: {'Yes (continuing)' if history else 'No (first time)'}")

    try:
        # Ensure history is never None
        if history is None:
            history = ""
        
        # Checks if this is truly a first-time greeting or a continuation
        is_first_time = not history or len(history.strip()) == 0
            
        template = """
            You are an English comprehension tutor who possesses good people skills.
            
            context:  
                Student's name: {name}
                Conversation history: {history}
                Is this the first interaction: {is_first_time}
                
            instructions:
                1. Look at the conversation history.
                2. If this is the FIRST interaction (no history):
                   - Greet the student warmly using their name
                   - Ask how they are feeling
                   - Ask if they are ready to study
                3. If there IS history (continuing conversation):
                   - Acknowledge you're continuing where you left off
                   - Reference the previous conversation briefly
                   - Ask if they'd like to continue or try something new
                4. Keep your response friendly, warm, and encouraging (2-3 sentences max)
        """

        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | llm | StrOutputParser()
        
        result = chain.invoke({
            "history": history, 
            "name": username,
            "is_first_time": str(is_first_time)
        })
        return result
    
    except Exception as e:
        print("Error in welcoming the user", e)
        return "Error communicating with the tutor" 

@tool    
def manage_dashboard_chat(
    username: str, 
    user_message: str, 
    history: str = Field(default="", description="Previous conversation history as a string"),
    summary_report: str = Field(default="", description="Summary report of the student's weaknesses in different skill components")
) -> str:
    """This function manages the ongoing conversation after an initial message has been sent to the user
    
    Args:
        username: The name of the student
        user_message: The current message from the student
        history: Previous conversation history as a string (optional, defaults to empty string)
        summary_report: Summary report of the student's weaknesses in different skill components (optional, defaults to empty string)
    """
    print("-------manage dashboard chat tool called with username:", username)
    print(f"       User message: '{user_message}'")
    print(f"       Has history: {bool(history)}")

    try:
        # Ensure history is never None
        if history is None:
            history = ""
        
        #HANDLE EMPTY MESSAGE (page reload with existing history)
        is_returning = not user_message or user_message.strip() == ""
            
        template = """
            You are a tutor to a student who wants to study English comprehension in a platform.
             
            context: 
                Student's Name: {name}
                Message from the student: {student_message}
                Chat history: {history}
                Summary report: {summary_report}
                Is student returning to dashboard: {is_returning}

            instructions:
                1. If the student is RETURNING (empty message, just loaded page):
                   - Welcome them back warmly
                   - Briefly remind them of what you discussed before
                   - Encourage them to continue studying on the study page
                   
                2. If the student sent an ACTUAL MESSAGE:
                   - Look at the chat history to see if you've already:
                     * Explained the platform features (study page, natural language interaction)
                     * Provided their weakness report based on summary
                     * Given advice on improving using the platform
                   - If you haven't done the above, do it now in a concise way (2-3 sentences)
                   - Then respond to their current message and encourage them to study
                   
                3. Keep responses short and encouraging (2-4 sentences max)
        """
        
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | llm | StrOutputParser()
        
        result = chain.invoke({
            "name": username, 
            "student_message": user_message if user_message else "(student returned to dashboard)", 
            "history": history,
            "summary_report": summary_report,
            "is_returning": str(is_returning)
        })
        
        return result
        
    except Exception as e:
        print("Error in managing chat", e)
        return "Error communicating with the tutor"
    
# Create tools list
tools = [initialise_dashboard_chat, manage_dashboard_chat]

# Create model with tools bound
dashboard_model = llm.bind_tools(tools)

def should_continue(state: generalChat) -> str:
    """Determines if we should continue to tools or end"""
    
    print(f"should_continue checking messages: {len(state.messages) if state.messages else 0} messages")
    ##print(f"-----------GIGIRIII{state.messages}-------------")
    
    # Check the last message for tool calls
    if state.messages:
        last_message = state.messages[-1]
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            print("Going to tools")
            return "tools"
    
    print("Going to end")
    return "end"

def dashboard_router(state: generalChat) -> generalChat:
    """Router function that determines which tool to use based on the conversation state"""
    print("=== ROUTER STARTED ===")
    
    message = state.user_message
    username = state.username
    summary_report = progress.get_report_summary(state.user_id) if state.user_id else "No report summary available"
    
    # Convert simple history list to string for tool compatibility
    history_str = ""
    if state.dashboard_history:
        history_parts = []
        for item in state.dashboard_history:
            if 'HumanMessage' in item:
                history_parts.append(f"Student: {item['HumanMessage']}")
            elif 'AIMessage' in item:
                history_parts.append(f"Tutor: {item['AIMessage']}")
        history_str = " | ".join(history_parts)
    
    # DETERMINE WHICH TOOL TO USE BASED ON CONVERSATION STATE
    has_history = bool(state.dashboard_history and len(state.dashboard_history) > 0)
    
    # Decision logic: if history exists, use manage; otherwise use initialise
    # Exception: if user explicitly says "restart" or "reload", use initialise
    is_explicit_restart = message.strip().lower() in ["restart", "reload", "start over", "begin fresh"]
    
    if has_history and not is_explicit_restart:
        tool_to_use = "manage_dashboard_chat"
        print(f"DECISION: Has {len(state.dashboard_history)} history messages → Using manage_dashboard_chat")
    else:
        tool_to_use = "initialise_dashboard_chat"
        print(f"DECISION: No history or explicit restart → Using initialise_dashboard_chat")
    
    # CREATE EXPLICIT INSTRUCTION FOR THE LLM
    system_message = SystemMessage(content=f"""
        You are a tool-calling assistant. You MUST call exactly one tool based on the instruction below.

        INSTRUCTION: Call the '{tool_to_use}' tool.

        Context (for your information):
        - Username: {username}
        - User message: "{message if message else '(empty - page load)'}"
        - Conversation history exists: {'Yes' if has_history else 'No'}
        - History length: {len(state.dashboard_history) if state.dashboard_history else 0}

        MANDATORY ACTION: Call {tool_to_use} with these parameters:
        {f'''- username: "{username}"
        - history: "{history_str}"''' if tool_to_use == "initialise_dashboard_chat" else f'''- username: "{username}"
        - user_message: "{message}"
        - history: "{history_str}"
        - summary_report: "{summary_report}"'''}

        Do not respond with text. Only make the tool call.
        """)
    
    # Create a simple user message
    user_message = HumanMessage(content=f"Execute the tool call for {tool_to_use}.")
    
    # Get AI response with tool calls
    ai_response = dashboard_model.invoke([system_message, user_message])
    
    # Add messages to state
    state.messages = [system_message, user_message, ai_response]
    
    print(f"Router completed. Tool selected: {tool_to_use}")
    if hasattr(ai_response, 'tool_calls') and ai_response.tool_calls:
        print(f"   Tool actually called: {ai_response.tool_calls[0]['name']}")
    print("=== ROUTER FINISHED ===")
    
    return state

def extract_final_message(state: generalChat) -> generalChat:
    """Extract the final message from tool results for the frontend"""
    print("=== EXTRACTING FINAL MESSAGE ===")

    #print(f"-----------OOOOHHHHHHHHH{state.messages}-------------")
    
    try:
        # The ToolNode adds ToolMessage responses to the messages
        # Find the last ToolMessage which contains our result
        for message in reversed(state.messages):
            if hasattr(message, 'content') and message.content and not isinstance(message, (SystemMessage, HumanMessage)):
                state.message = str(message.content)
                #print(f"Extracted message: {state.message}")
                break
        
        if not state.message:
            state.message = "No response generated"
        
    except Exception as e:
        #print(f"Error extracting message: {e}")
        state.message = "Error processing response"
    
    return state

def dashboard_graph():
    """Creates and returns the compiled dashboard graph"""
    
    # Create the graph with your custom state
    graph = StateGraph(generalChat)
    
    # Create tool node using LangGraph's built-in ToolNode
    tool_node = ToolNode(tools)
    
    # Add nodes
    graph.add_node("agent", dashboard_router)
    graph.add_node("tools", tool_node)
    graph.add_node("extract", extract_final_message)
    
    # Set entry point
    graph.set_entry_point("agent")
    
    # Add conditional edges from agent
    graph.add_conditional_edges(
        "agent",
        should_continue, 
        {
            "tools": "tools",
            "end": "extract"
        }
    )

    graph.add_edge("tools", "extract")
    graph.add_edge("extract", END)

    return graph.compile()


