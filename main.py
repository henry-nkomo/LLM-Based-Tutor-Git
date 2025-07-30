from flask import Flask, render_template, request, jsonify
import re
import json
from langchain_core.runnables import RunnablePassthrough
import PyPDF2
from PyPDF2 import PdfReader
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage 
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os
"""new items starts here"""
from flask import Flask, request, session, redirect, url_for, render_template
from flask_sqlalchemy import SQLAlchemy 
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import time
from werkzeug.security import generate_password_hash, check_password_hash
from pydantic import BaseModel, ValidationError
from typing import Optional, List
"""and ends here"""

app = Flask(__name__)
from dotenv import load_dotenv
load_dotenv()
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#uncomment for testing for seconds app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=10)  # Session expires in 10 seconds
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)
app.config['SESSION_PERMANENT'] = True

# Session timeout configuration
#uncoment when testing for seconds SESSION_TIMEOUT_SECONDS = 10
SESSION_TIMEOUT_MINUTES = 10 #10 minutes

db = SQLAlchemy(app)

#configure LLM model
google_api_key =  os.getenv('GOOGLE_API_KEY')
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3, google_api_key = google_api_key)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  
    email = db.Column(db.String(100), nullable=False, unique=True)  
    password = db.Column(db.String(255), nullable=False)
    l_completed = db.Column(db.Integer, default=0)
    c_mark = db.Column(db.Integer, default=0)
    c_id = db.Column(db.Integer, default=0)
    s_mark = db.Column(db.Integer, default=0)
    s_id = db.Column(db.Integer, default=0)
    v_mark = db.Column(db.Integer, default=0)
    v_id = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<User {self.name}>'

#############################################################################
#####           Login Logout SignUp Management
#############################################################################

@app.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        

        name = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not name or not email or not password:
            return jsonify({'error': 'Username, email, and password are required'}), 400
        
        # Hash password
        password_hash = generate_password_hash(password)
        
        #check if email has been used
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'User with that email exist try another one'}), 400
        
        # Create user
        new_user = User(name=name, email=email, password=password_hash)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            
            # Log user in
            session['username'] = name
            
            return jsonify({
                'message': 'User created successfully',
                'user_id': new_user.id,
                'username': new_user.name
            }), 201
            
        except IntegrityError:
            db.session.rollback()
            return jsonify({'error': 'Username or email already exists'}), 400
            
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'An error occurred'}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        user = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not user:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Find user by email, name and check password
        user_object = User.query.filter_by(email=user).first()
        #user_password = check_password_hash(user.password, password)
        
        if not user_object or not check_password_hash(user_object.password, password):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Check password
        #if not user_password:
            #return jsonify({'error': 'Invalid email or password'}), 401
        
        # Create session with TTL
        session.permanent = True  # Enable permanent session
        session['user_id'] = user_object.id
        session['username'] = user_object.name
        session['login_time'] = time.time()  # Store login timestamp
        session['last_activity'] = time.time()  # Track activity for inactivity-based expiration
        session['welcome_dialogue'] = []
        session['summary_dialogue'] = []
        session['comprehension_dialogue'] = []
        session['mark'] = []
        
        return jsonify({
            'message': 'Login successful',
            'user_id': user_object.id,
            'username': user_object.name,
            'session_expires_in': str(app.config['PERMANENT_SESSION_LIFETIME'])
        }), 200
        
    except Exception as e:
         print(str(e))
         return jsonify({'error': 'An error occurred during login'}), 500

@app.route('/logout', methods=['POST'])
def logout():
    """Logout route to clear session"""
    session.clear()
    #global welcome_user_dialogue
    #del welcome_user_dialogue
    return jsonify({'message': 'Logged out successfully'}), 200

# Middleware to check authentication for protected routes
def login_required(f):
    """Decorator to protect routes that require authentication"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return render_template('main.html')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('options.html')

##############################################################
#####         Session Management
##############################################################

@app.route('/check-session', methods=['GET'])
def check_session():
    """Check and update session activity"""
    if 'user_id' not in session:
        return jsonify({'authenticated': False, 'message': 'No active session'}), 401
    
    # Update last activity time
    session['last_activity'] = time.time()

    entry3 = User.query.filter_by(id=session['user_id']).first()  

    if entry3:
        lessons = entry3.l_completed
        c_mark = entry3.c_mark
        s_mark = entry3.s_mark
    
    return jsonify({
        'authenticated': True,
        'user_id': session['user_id'],
        'username': session['username'],
        'l_completed': lessons,
        'c_mark': c_mark,
        's_mark': s_mark,
        'last_activity': datetime.fromtimestamp(session['last_activity']).isoformat(),
        'session_timeout': SESSION_TIMEOUT_MINUTES
        #uncomment after testing for seconds 'session_timeout': SESSION_TIMEOUT_MINUTES * 60
    }), 200

@app.route('/extend-session', methods=['POST'])
def extend_session():
    """Explicitly extend session - called by frontend when user is active"""
    if 'user_id' not in session:
        return jsonify({'authenticated': False, 'message': 'No active session'}), 401
    
    # Update last activity time
    session['last_activity'] = time.time()
    
    return jsonify({
        'message': 'Session extended',
        'last_activity': datetime.fromtimestamp(session['last_activity']).isoformat(),
        'expires_in_seconds': SESSION_TIMEOUT_MINUTES
        #uncomment after testing for seconds 'expires_in_seconds': SESSION_TIMEOUT_MINUTES * 60
    }), 200

@app.route('/session-status', methods=['GET'])
def session_status():
    """Get detailed session information"""
    if 'user_id' not in session:
        return jsonify({'authenticated': False}), 401
    
    login_time = session.get('login_time')
    last_activity = session.get('last_activity')
    current_time = time.time()
    
    # Calculate time remaining
    time_since_activity = current_time - last_activity if last_activity else 0
    #time_remaining = SESSION_TIMEOUT_SECONDS - time_since_activity
    time_remaining = (SESSION_TIMEOUT_MINUTES * 60) - time_remaining

    return jsonify({
        'authenticated': True,
        'user_id': session['user_id'],
        'username': session['username'],
        'login_time': datetime.fromtimestamp(login_time).isoformat() if login_time else None,
        'last_activity': datetime.fromtimestamp(last_activity).isoformat() if last_activity else None,
        'time_since_activity_seconds': int(time_since_activity),
        'time_remaining_seconds': max(0, int(time_remaining)),
        'expires_soon': time_remaining <= (8 * 60)  # True if expires in 2 minutes or less
    }), 200

##############################################################
######## Study Meterial Database
##############################################################
class studyMeterial(db.Model):
    __tablename__ = 'study_meterial'
    id = db.Column(db.Integer, primary_key=True)
    passage = db.Column(db.Text, nullable=False)
    questions = db.Column(db.JSON, nullable=False)

def retrieve_passage(meterial_id):
    meterial_id = meterial_id
    meterial =studyMeterial.query.filter_by(id=meterial_id).first()
    try: 
        if meterial:
          return meterial.passage
        else:
          return None
    except Exception as e:
        print(f"failed to retrieve passage at {meterial_id}: {e}")

######################################################
#######     Chat Area
######################################################

################################ Welcome Dialogue For Dashboard Page ##############################

@app.route('/welcome-user', methods=['GET'])
def welcome_user():
    try:
        history = session['welcome_dialogue']

        template = """
            You are tutor. This is supposed to be a dialogue you had with the student: {history}, if nothing is in the dialoge don't worry
            Greet the Student using their name: {name} you can continue the convesation based on the previous dialogue. If you had not asked the student,
            ask them how they are feeling at the moment and if they are ready to for study.  
        """

        prompt = ChatPromptTemplate.from_template(template)
        retrieval_chain = (
            {"history": lambda x: history, "name": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )

        response1  = retrieval_chain.invoke({"name": session['username']})

        session['welcome_dialogue'].append({"AIMessage": response1})

        return jsonify({
            'message': response1, 
            'dialogue': session['welcome_dialogue']
        }), 200
    except Exception as e:
        print("Error in welcoming the user", e)
        return jsonify({'error': 'Failed to welcome user'}), 500

@app.route('/welcome-dialogue', methods = ['POST'])
def welcome_dialogue():
    data = request.get_json()
    user_message = data.get('message')

    try:
        template = """
            You are a tutor, to a student who wants to study English comprehension in a platform. This is  the name of your student: {name}. 
            This is the message from the student : {student_message}. The platform has three sections question answering, summary writing and 
            vocabulary questions all based on a reading passage to help students master English comprehension.
            Mention either one or all of these to the student and ask of the student's weaknesses on them.
            After this you may engage in a conversation telling the student how to master the areas. When you have mentioned to the student how to master these areas,
            tell the student to select a study option, there are dedicated sections for all of the three study options in the platform
            so you don't tutor them directly here but you can encourage them to click on the study option and start studying in the platform.
            Respond to the student's message considering this chat history you have with the student: {history} mantain the conversation on 
            academics, English comprehension skills. Your responses should be short and precise.

        """
        prompt3 = ChatPromptTemplate.from_template(template)

        retrieval_chain = (
            {"name": lambda x: session['username'], "student_message": lambda x: user_message, "history": RunnablePassthrough()}
            | prompt3
            | llm
            | StrOutputParser()
        )

        response = retrieval_chain.invoke({"history": session['welcome_dialogue']})

        session['welcome_dialogue'].append({"HumanMessage": user_message})
        session['welcome_dialogue'].append({"AIMessage": response})

        return jsonify({
            'message': response
        }), 200
    except Exception as e:
        print("Error in welcoming the user", e)
        return jsonify({'error': 'Failed to welcome user dialogue'}), 500

##########################                                               ################################   
########################## Comprehension Dialogue For Comprehension Page ################################

class compState(BaseModel):
    response: str
    state: Optional[str] = None
    mark: Optional[int] = None
    question_num: Optional[int] = None
    attempts: Optional[int] = None
    feedback: Optional[str] = None

def compEdge(state: compState):
    return state.state

comp_traverse = False

compState_instance = compState(response ="No response yet", state = "first", question_num = 0, attempts=0)

def compFirstState(state: compState, user_response: str) -> compState:
    row = User.query.filter_by(id=session['user_id']).first() 
    meterial_id = row.c_id + 1
    meterial =studyMeterial.query.filter_by(id=meterial_id).first()
    questions = meterial.questions

    template = """
        You are a tutor your student's name is {name} . You are about to begin a session with a 
        student to study English comprehension question answering which is an option they have selected.
        Contintue a dialogue based on this history: {history} and this is their current message: {message} respond to it.
        While engaging in the dialogue, assess if a student is ready to study if they are ready set the state to second 
        if they are not ready set the state to first. Your approach should be of a tutor welcoming the student into the study session.
        .Respond ONLY in a JSON format as {{"response": "<your message>", "state": "second" or "first"}}.
    """
    prompt3 = ChatPromptTemplate.from_template(template)

    retrieval_chain = (
        {"history": lambda x: session['welcome_dialogue'], "message": lambda x: user_response, "name": RunnablePassthrough()}
        | prompt3
        | llm
        | StrOutputParser()
    )

    feedback = retrieval_chain.invoke(session['username'])
    feedback = feedback.strip()

    response = re.sub(r"```json\s*|\s*```", "", feedback.strip())

    try:
        data = json.loads(response)
        # Validate using Pydantic
        temporary_state = compState(**data)

        for field_name in state.model_fields:
            new_value = getattr(temporary_state , field_name)

            if new_value is not None:
                setattr(state, field_name, new_value)

        if state.state == "second":
            state.response = questions[state.question_num]
            #state.question_num = state.question_num + 1 
            print(state)

        session['comprehension_dialogue'].append({"HumanMessage": user_response})
        session['comprehension_dialogue'].append({"AIMessage": state.response})
        return state
    except (json.JSONDecodeError, ValidationError) as e:
        print(f"Failed to parse or validate LLM output: {e}")
        # Return a fallback state
        return compState(response="Sorry, I could not process your input correctly.", state = "first", mark = state.mark, question_num = state.question_num, attempts= state.attempts, feedback= state.feedback)


def compSecondState(state: compState, user_response: str) -> compState:
    #mechanism to adjust difficulty
    row = User.query.filter_by(id=session['user_id']).first() 
    meterial_id = row.c_id + 1
    meterial =studyMeterial.query.filter_by(id=meterial_id).first()
    passage = meterial.passage
    questions = meterial.questions
    global comp_traverse

    session['comprehension_dialogue'].append({"HumanMessage": user_response})
    print(f"************{questions[state.question_num]}***********************")

    if state.question_num == len(questions):  # leave it like that we want to triger state change after we traversed through all the questions in the array
        state.state = "third"
        comp_traverse = True
        return
    
    if state.attempts < 3:
    
        template = """
            You are a tutor marking english comprehension writing, this is the message from the student: {answer} they are supposed to answer to the 
            question: {question} based on the comprehension passage: {passage} their response may or may not be an answer to the question asked. 
            If their response is not an answer respond to it accordingly offer assistance if needed but do not give out answers directly
            then emphasise that they should try to answer the
            question asked, they are given a limited number of attempts {attempts} mention them and mark that as general in the feedback section, respond ONLY in JSON format as 
            {{"response": <your response>, "feedback": "general"}}. If they sent what seems to be an 
            answer, mark it as either correct even if it is partially correct or wrong if it is totally wrong in the feedback section,
            respond ONLY in JSON format as {{"response": <your response>, "feedback": "correct" or "wrong"}}
        """
        prompt3 = ChatPromptTemplate.from_template(template)

        retrieval_chain = (
            {"answer": lambda x: user_response, "question": lambda x: questions[state.question_num], "attempts": lambda x: 3 - state.attempts, "passage": RunnablePassthrough()}
            | prompt3
            | llm
            | StrOutputParser()
        )

        feedback = retrieval_chain.invoke(passage)
        first_response = re.sub(r"```json\s*|\s*```", "", feedback.strip())

        try:
            data = json.loads(first_response)
            # Validate using Pydantic

            temporary_state = compState(**data)

            for field_name in state.model_fields:
                new_value = getattr(temporary_state , field_name)

                if new_value is not None:
                    setattr(state, field_name, new_value)

            state.attempts = state.attempts + 1
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"Failed to parse or validate LLM output: {e}")
            # Return a fallback state
            return compState(response="Sorry, I could not process your input correctly.", state = "second", mark = state.mark, question_num = state.question_num, attempts= state.attempts, feedback= state.feedback)

        if state.feedback == "general":
            session['comprehension_dialogue'].append({"AIMessage": state.response})
            return state

        if state.feedback == "correct":
            state.question_num = state.question_num + 1

            template = """
                        You are a tutor and a student has just answered a question correctly. It can be partially correct, in that case tell them what 
                        they might have missed and give a mark out of 2 or it can be entirely correct, in that case, 
                        tell them something good give a mark out of 2. In your response tell them to answer the 
                        next question, print the next question as well exactly as it is. This is the next question: {question}. 
                        respond ONLY in JSON format as {{"response": <your response>, "mark": "mark"}}"
                    """
            
            prompt4 = ChatPromptTemplate.from_template(template)

            retrieval_chain = (
                    {"question": RunnablePassthrough()}
                    |prompt4
                    |llm
                    |StrOutputParser()
            )

            feedback = retrieval_chain.invoke({"question": questions[state.question_num]})
            first_response = re.sub(r"```json\s*|\s*```", "", feedback.strip())

            try:
                data = json.loads(first_response)
                temporary_state = compState(**data)

                for field_name in state.model_fields:
                    new_value = getattr(temporary_state , field_name)

                    if new_value is not None:
                        setattr(state, field_name, new_value)
                session['mark'].append(state.mark)
                session['comprehension_dialogue'].append({"AIMessage": state.response})
                return state
            except (json.JSONDecodeError, ValidationError) as e:
                print(f"Failed to parse or validate LLM output: {e}")
                # Return a fallback state
                return compState(response="Sorry, I could not process your input correctly.", state = "second", mark = state.mark, question_num = state.question_num, attempts= state.attempts, feedback= state.feedback)

        if state.feedback =="wrong":
            template = """
                        You are a tutor and your student has just answered this question: {question} from this comprehension passage: {passage}. 
                        Their response was wrong. Provide hints to guide them towards the correct 
                        answer from the comprehension passage without giving the answer directly be brief and precide. Encourage them to think 
                        critically and try answering 
                        the question again respond ONLY in JSON format as {{"response": <your response>}}"
                    """
            prompt4 = ChatPromptTemplate.from_template(template)

            retrieval_chain = (
                    {"question": lambda x: questions[state.question_num], "question": RunnablePassthrough()}
                    |prompt4
                    |llm
                    |StrOutputParser()
            )

            feedback = retrieval_chain.invoke({"question": questions[state.question_num]})
            first_response = re.sub(r"```json\s*|\s*```", "", feedback.strip())


            try:
                data = json.loads(first_response)
                temporary_state = compState(**data)

                for field_name in state.model_fields:
                    new_value = getattr(temporary_state , field_name)

                    if new_value is not None:
                        setattr(state, field_name, new_value)
                session['comprehension_dialogue'].append({"AIMessage": state.response})
                return state
            
            except (json.JSONDecodeError, ValidationError) as e:
                print(f"Failed to parse or validate LLM output: {e}")
                # Return a fallback state
                return compState(response="Sorry, I could not process your input correctly.", state = "second", mark = state.mark, question_num = state.question_num, attempts= state.attempts, feedback= state.feedback)
        
    if state.attempts == 3:
        template = """
                You are a tutor and a student has just finished the number of attempts they are given to answer,
                    a question tell them the answer and how they could have obtained it and that they should move 
                onto the next question {next_question} include the question in your response respond ONLY in JSON format as
                    {{"response": <your response>}}.
            """
    
        prompt4 = ChatPromptTemplate.from_template(template)

        retrieval_chain = (
                {"next_question": RunnablePassthrough()}
                |prompt4
                |llm
                |StrOutputParser()
        )

        feedback = retrieval_chain.invoke({"next_question": questions[state.question_num + 1]})
        first_response = re.sub(r"```json\s*|\s*```", "", feedback.strip())

        try:
            data = json.loads(first_response)
            temporary_state = compState(**data)

            for field_name in state.model_fields:
                new_value = getattr(temporary_state , field_name)

                if new_value is not None:
                    setattr(state, field_name, new_value)
            state.attempts = 0
            session['mark'].append(0)
            session['comprehension_dialogue'].append({"AIMessage": state.response})
            return state
        
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"Failed to parse or validate LLM output: {e}")
            # Return a fallback state
            return compState(response="Sorry, I could not process your input correctly.", state = "second", mark = state.mark, question_num = state.question_num, attempts= state.attempts, feedback= state.feedback)
    

def compThirdState(state: compState, user_response: str) -> compState:  

    if comp_traverse:
        total = 0
        count = 0

        for num in session('mark'):
            total = total + num
            count = count + 1

        mark = (total / (count * 2)) * 100
        
        try:
            entry = User.query.filter_by(id=session['user_id']).first() 
            if entry:
                entry.l_completed = entry.l_completed + 1
                entry.c_mark = mark/(entry.c_id + 1)
                entry.c_id = entry.c_id + 1
                db.session.commit()
                comp_traverse = False
            else:
                print("error adding entry")
        except Exception as e:
            db.session.rollback()
            print("error", e)

    template = """
        You are a tutor you had an english comprehension tutoring session with a student. 
        This is the current message from the student: {message}. Tell them to go back to the dashboard session and pick another study option. Your approach should be of a person 
        who want to end the current dialogue. Respond ONLY in JSON format as {{"response": <your response>}}.
    """
    prompt3 = ChatPromptTemplate.from_template(template)

    retrieval_chain = (
        {"history": RunnablePassthrough()}
        | prompt3
        | llm
        | StrOutputParser()
    )

    feedback =  retrieval_chain.invoke(user_response)
    first_response = re.sub(r"```json\s*|\s*```", "", feedback.strip())

    try:
        data = json.loads(first_response)
        temporary_state = compState(**data)

        for field_name in state.model_fields:
            new_value = getattr(temporary_state , field_name)

            if new_value is not None:
                setattr(state, field_name, new_value)
        session['welcome_dialogue'].append({"AIMessage": state.response})
        return state

    except (json.JSONDecodeError, ValidationError) as e:
        print(f"Failed to parse or validate LLM output: {e}")
        # Return a fallback state
        return compState(response="Sorry, I could not process your input correctly.", state = "third", mark = state.mark, question_num = state.question_num, attempts= state.attempts, feedback= state.feedback)

###################################                                   ##################################
################################### Summary dialogue for summary page ##################################
class sumState(BaseModel):
    response: str
    state: str
    mark: int = 0

sumState_instance = sumState(response="waiting for system response", state="first")

sum_traverse = True

def sumEdge(state: sumState):
    return state.state

def sumFirstState(state: sumState, user_message: str) -> sumState:

    question = """Read the Comprehension passage and summarise the MAIN POINTS \n List SEVEN points in full sentences .
                     \n Number your sentences from 1 to 7. \n Use your OWN words as far as possible. \n Indicate the total number of words you have
                       used in brackets at the end of your summary."""

    template = """
        You are a tutor your student's name is {name} . You are about to begin a session with a 
        student to study English summary writing which is an option they have selected.
        Contintue a dialogue based on this history: {history} if it is empty do not worry, and this is their current message: {message} respond to it.
        Assess if a student is ready to study if they are ready we can move to the second state of the conversation else we remain in our first
        .Respond ONLY in a JSON format as {{"response": "<your message>", "state": "second" or "first"}}.
    """
    prompt3 = ChatPromptTemplate.from_template(template)

    retrieval_chain = (
        {"history": lambda x: session['welcome_dialogue'], "message": lambda x: user_message, "name": RunnablePassthrough()}
        | prompt3
        | llm
        | StrOutputParser()
    )

    feedback = retrieval_chain.invoke(session['username'])
    response = re.sub(r"```json\s*|\s*```", "", feedback.strip())
    try:
        data = json.loads(response)
        # Validate using Pydantic
        state = sumState(**data)
        if state.state == "second":
            state.response = question
        session['summary_dialogue'].append({"HumanMessage": user_message})
        session['summary_dialogue'].append({"AIMessage": state.response})
        return state
    except (json.JSONDecodeError, ValidationError) as e:
        print(f"Failed to parse or validate LLM output: {e}")
        # Return a fallback state
        return sumState(response="Sorry, I could not process your input correctly.", state = "first")

def sumSecondState(state: sumState, user_message: str) -> sumState:
    #mechanism to adjust difficulty
    row = User.query.filter_by(id=session['user_id']).first() 
    meterial_id = row.s_id + 1
    passage = retrieve_passage(meterial_id)

    question = """Read the Comprehension passage and summarise the MAIN POINTS \n List SEVEN points in full sentences using approximately 70 words.
                     \n Number your sentences from 1 to 7. \n Use your OWN words as far as possible. \n Indicate the total number of words you have
                       used in brackets at the end of your summary."""
    
    template = """
        You are a tutor marking english summary writing, this is the message from the student: {answer} they are supposed to answer to the 
        question: {question} 
        based on the comprehension passage: {passage}. If they sent a general message respond to it emphasising that they should answer the
        question asked and respond ONLY in JSON format as {{"response": <your response>, "state": "second"}}. 
        If they sent what seems to be an answer, give the student your feedback assessment which is short and precise, do not be strict begin by reminding them 
        on the rules of summary writing as stipulated in the question if they did not follow any them point out where they can improve on their 
        summary writing. Also score their writing out of 10 marks mention their mark in your response also and for this 
        Respond ONLY in JSON format as {{"response": <your response>, "state": "third", "mark": <student's mark>}}
    """
    prompt3 = ChatPromptTemplate.from_template(template)

    retrieval_chain = (
        {"answer": lambda x: user_message, "question": lambda x: question, "passage": RunnablePassthrough()}
        | prompt3
        | llm
        | StrOutputParser()
    )

    feedback = retrieval_chain.invoke(passage)
    response =  re.sub(r"```json\s*|\s*```", "", feedback.strip())

    try:
        data = json.loads(response)
        # Validate using Pydantic
        state = sumState(**data)
        session['summary_dialogue'].append({"HumanMessage": user_message})
        session['summary_dialogue'].append({"AIMessage": state.response})
        return state
    except (json.JSONDecodeError, ValidationError) as e:
        print(f"Failed to parse or validate LLM output: {e}")
        # Return a fallback state
        return sumState(response="Sorry, I could not process your input correctly.", state ="second")

def sumThirdState(state: sumState, user_message: str) -> sumState: 
    global sum_traverse

    if sum_traverse:

        mark = (state.mark / 10) * 100
        
        try:
            entry2 = User.query.get(session['user_id'])
            if entry2:
                entry2.l_completed = entry2.l_completed + 1
                entry2.s_mark = mark/(entry2.c_id + 1)
                entry2.s_id = entry2.c_id + 1
                db.session.commit()
                sum_traverse = False
            else:
                print("error adding entry")
        except Exception as e:
            db.session.rollback()
            print("error", e)

    template = """
        You are a tutor you had an english summary writing tutoring session with a student. This is the dialogue you had: {history}.
        This is the current message from the student: {message}. Tell them to go back to the dashboard session and pick another study option. 
        Your approach should be of a person who wants to end the current dialogue. Respond ONLY in JSON format as 
        {{"response": <your response>, "state": "third"}}
    """
    prompt3 = ChatPromptTemplate.from_template(template)

    retrieval_chain = (
        {"message": lambda x: user_message, "history": RunnablePassthrough()}
        | prompt3
        | llm
        | StrOutputParser()
    )

    feedback = retrieval_chain.invoke(session['summary_dialogue'])
    response = re.sub(r"```json\s*|\s*```", "", feedback.strip())

    try:
        data = json.loads(response)
        # Validate using Pydantic
        state = sumState(**data)
        session['summary_dialogue'].append({"HumanMessage": user_message})
        session['summary_dialogue'].append({"AIMessage": state.response})
        return state
    except (json.JSONDecodeError, ValidationError) as e:
        print(f"Failed to parse or validate LLM output: {e}")
        # Return a fallback state
        return sumState(ready="no", response="Sorry, I could not process your input correctly.")


def clean_llm_json(llm_output):
    # Remove markdown code fences and extra whitespace
    cleaned = re.sub(r"```json\s*|\s*```", "", llm_output.strip())
    return json.loads(cleaned)

def generate_vocabulary_que():
    row = User.query.filter_by(id=session['user_id']).first() 
    meterial_id = row.v_id + 1
    passage = retrieve_passage(meterial_id)
    template = """
            You are a tutor, helping a grade 12 student with vocabulary. Given the passage {passage}, generate 4 vocabulary question to assess a student's vocabulary. provide answers for the student to choose from 1 correct and 4 wrong answers. give a response as a JSON format. your response should contain only the question, answers and the correct answer
        """
    prompt3 = ChatPromptTemplate.from_template(template)

    retrieval_chain = (
        {"passage": RunnablePassthrough()}
        | prompt3
        | llm
        | StrOutputParser()
    )

    voc_questions = retrieval_chain.invoke({"passage": passage})

    return voc_questions

@app.route('/comp-welcome-dialogue', methods = ['GET'])
def comp_welcome_dialogue():

    #check for previous dialogue
    if len(session['comprehension_dialogue']) >= 2:
        return jsonify({'dialogue': session['comprehension_dialogue']})

    try:
        template = """
            You are a tutor this is  the name of yor student: {name}. This is the previous dialogue you had with the student: {history}. 
            If the dialogue is empty do not worry continue to chat with the student. Greet them ask if they are ready to study English comprehension
            skills question question answering which is an option they have selected.
        """
        prompt3 = ChatPromptTemplate.from_template(template)

        retrieval_chain = (
            {"name": lambda x: session['username'], "history": RunnablePassthrough()}
            | prompt3
            | llm
            | StrOutputParser()
        )

        response = retrieval_chain.invoke(session['welcome_dialogue'])

        session['comprehension_dialogue'].append({"AIMessage": response}) 

        return jsonify({
            'message': response
        }), 200
    except Exception as e:
        print("Error in welcoming the user", e)
        return jsonify({'error': 'Failed to welcome user dialogue'}), 500

@app.route('/comp-dialogue', methods = ['POST'])
def comp_dialogue():
    global com_state
    data = request.get_json()
    user_message = data.get('message')
    ############# use try catch blocks in state functions implement proper error handling

    global compState_instance
    conversation_state = compEdge(compState_instance)
  
    if conversation_state == 'first':
        compState_instance = compFirstState(compState_instance,user_message)

        response = compState_instance.response

    elif conversation_state ==  'second':
        compState_instance = compSecondState(compState_instance, user_message)

        response = compState_instance.response

    elif conversation_state == 'third':
        compState_instance = compThirdState(compState_instance,user_message)

        response = compState_instance.response

    return jsonify({'message': response}), 200

@app.route('/sum-welcome-dialogue', methods = ['GET'])
def sum_welcome_dialogue():
    
    if len(session['summary_dialogue']) >= 2:
        return jsonify({'dialogue': session['summary_dialogue']})
    
    try:
        template = """
            You are a tutor this is  the name of yor student: {name}. This is the previous dialogue you had with the student: {history}. 
            If the dialogue is empty do not worry continue to chat with the student. Greet them ask if they are ready to study 
            English summary writing which is an option they have selected.
        """
        prompt3 = ChatPromptTemplate.from_template(template)

        retrieval_chain = (
            {"name": lambda x: session['username'], "history": RunnablePassthrough()}
            | prompt3
            | llm
            | StrOutputParser()
        )

        response = retrieval_chain.invoke(session['welcome_dialogue'])

        session['summary_dialogue'].append({"AIMessage": response})
        

        return jsonify({
            'message': response
        }), 200
    except Exception as e:
        print("Error in welcoming the user", e)
        return jsonify({'error': 'Failed to welcome user dialogue'}), 500
    
@app.route('/sum-dialogue', methods = ['POST'])
def sum_dialogue():
    global com_state
    data = request.get_json()
    user_message = data.get('message')
    ############# use try catch blocks in state functions implement proper error handling
    global sumState_instance
    conversation_state = sumEdge(sumState_instance)
  
    if conversation_state == 'first':
        sumState_instance = sumFirstState(sumState_instance,user_message)

        response = sumState_instance.response

    elif conversation_state ==  'second':
        sumState_instance = sumSecondState(sumState_instance, user_message)

        response = sumState_instance.response

    elif conversation_state == 'third':
        sumState_instance = sumThirdState(sumState_instance,user_message)

        response = sumState_instance.response

    return jsonify({'message': response}), 200


##################################################################
##########   Handle Simple Routes
#################################################################

@app.route('/')
def home():
    return render_template('main.html')

@app.route('/another-page')
def another_page():
    return render_template('upload.html')

@app.route('/get-comprehension', methods = ['GET'])
def get_comprehension():
    if 'user_id' in session:
        row = User.query.filter_by(id=session['user_id']).first() 
        meterial_id = row.c_id + 1
        passage = retrieve_passage(meterial_id)
        return render_template('comprehension.html', text = passage)
    else:
        return render_template('main.html'), 401

@app.route('/get-summary', methods = ['GET'])
def get_summary():
    if 'user_id' in session:
        row = User.query.filter_by(id=session['user_id']).first() 
        meterial_id = row.s_id + 1
        passage = retrieve_passage(meterial_id)
        return render_template('summary.html', text = passage)
    else:
        return render_template('main.html'), 401
    
@app.route('/get-vocabulary', methods = ['GET'])
def get_vocabulary():
    if 'user_id' in session:
        meterial_id = 1  #change later this value should be obtained from table user
        passage = retrieve_passage(meterial_id)
        return render_template('vocabulary.html', text = passage)
    else:
        return render_template('main.html'), 401

@app.route('/get-vocabulary-questions', methods = ['GET'])
def get_vocabulary_questions():
    try:
        data = generate_vocabulary_que()
        clean_data = clean_llm_json(data)
        return jsonify({'message': clean_data}), 200
    except Exception as e:
        print("Error getting vocabulary questions:", e)
        return jsonify({'error': 'Failed to get study meterial'}), 500
   
if __name__ == '__main__':
    with app.app_context():
        #db.drop_all()
        db.create_all()
    app.run(debug=True)