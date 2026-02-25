from flask import Flask, jsonify, request, session, render_template
from project_files import db, create_app
from project_files.db_models import Users, trackProgress
from project_files.add_retrieve_data import retrieveData
from project_files.tools import tutor_graph, dashboard_graph
from project_files.state import mainState
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import time, math
from openai import OpenAI

app = create_app()

app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=20)
app.config['SESSION_PERMANENT'] = True

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
        
        # Check if email has been used
        existing_user = Users.query.filter_by(email=email).first()
        print(f"Existing user check: {existing_user}")  # Debug line
        
        if existing_user:
            return jsonify({'error': 'User with that email exist try another one'}), 400
        
        # Create user
        new_user = Users(name=name, email=email, password=password_hash)
        db.session.add(new_user)
        db.session.flush()  # This assigns the ID without committing
        
        print(f"New user ID: {new_user.id}")  # Debug line
        
        # Create progress with the new user's ID
        new_progress = trackProgress(
            user_id=new_user.id, 
            report_summary = " ", 
            skills_component={
                'comprehending-text': 10, 'summarisation': 10, 'vocabulary': 10
            }
        )
        
        db.session.add(new_progress)
        db.session.commit()
        
        # Log user in
        session['username'] = name
        
        return jsonify({    
            'message': 'User created successfully',
            'user_id': new_user.id,
            'username': new_user.name
        }), 201
            
    except IntegrityError as e:
        db.session.rollback()
        print(f"IntegrityError: {str(e)}")  # Debug line
        return jsonify({'error': f'Database integrity error: {str(e)}'}), 400
            
    except Exception as e:
        db.session.rollback()
        print(f"Exception: {str(e)}")  # Debug line
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500
    
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
        user_object = Users.query.filter_by(email=user).first()
        #user_password = check_password_hash(user.password, password)
        
        if not user_object or not check_password_hash(user_object.password, password):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Check password
        #if not user_password:
            #return jsonify({'error': 'Invalid email or password'}), 401

        progress = trackProgress.query.filter_by(user_id=user_object.id).first()
        if not progress:
            return jsonify({'error': 'No progress record found for the User '}), 404


        # Create session with TTL
        session.permanent = True  # Enable permanent session
        session['user_id'] = user_object.id
        session['username'] = user_object.name
        session['dash_history'] = []
        session['tutoring_history'] = []
        session['dashboard_history'] = []
        session['mark'] = []
        session['attempts'] = 0
        session['ai_response'] = "" 
        session['current_state'] = 'preamble'
        session['current_tutor_message'] = ''
        session['current_question'] = ''
        session['progress'] = progress.skills_component
        session['target_skill'] = ''
        
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

@app.route('/user-infor', methods=['GET'])
def user_info():
    if 'user_id' in session:
        return jsonify({
            'user_id': session['user_id'],
            'username': session['username'],
            'progress': session['progress']
        })
    else:
        return jsonify({'error': 'Not authenticated'}), 401

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/settings', methods = ['GET'])
def settings():
    if 'user_id' in session:
        return render_template('settings.html')
    else:
        return render_template('main.html'), 401
    
@app.route('/check-session')
def check_session():
    if 'user_id' in session:
        skill_components = retrieveData()
        # Fetch skill components from database
        skill_components_data = skill_components.get_skill_components(session['user_id'])
        
        return jsonify({
            'authenticated': True,
            'username': session.get('username'),
            'knowledge_state': skill_components_data  
        })
    else:
        return jsonify({'authenticated': False})
##################################################################
##########   Handle Chat Routes AKA Application Logic
#################################################################

@app.route('/dashboard_dialogue', methods=['POST'])
def dashboard_dialogue():
    try:
        data = request.get_json()
        user_message = data.get('message', '')  # Default to empty string

        default_input_response = "A message sent to the tutor has been flagged unsfafe and cannot be processed. Please ensure that any message sent does elicit or include harmful content spanning harassment, hate speech, illicit activities, self-harm, sexual content or violence "
        default_output_response = "A message from the tutor been flagged as unsafe and cannot be processed. Please resend you previous message to continue the tutoring session."

        client = OpenAI()

        input_moderation = client.moderations.create(
            model="omni-moderation-latest",
            input= user_message,
        )

        input_moderated_response = input_moderation.results[0]

        if input_moderated_response.flagged:
            return jsonify({"message": default_input_response}), 200

        #Initialize dashboard_history if it doesn't exist
        if 'dashboard_history' not in session:
            session['dashboard_history'] = []

        #Get existing history
        dashboard_history = session.get('dashboard_history', [])

        print(f"REQUEST: Message='{user_message}', History length={len(dashboard_history)}")

        state = {
            "user_message": user_message,
            "username": session['username'],
            "user_id": session['user_id'],
            "dashboard_history": dashboard_history,  
        }
        
        graph_builder = dashboard_graph()
        result = graph_builder.invoke(state)

        print("*****************///////-----------")
        print(result, "-------**/*//*****************************dashboard result")

        output_moderation = client.moderations.create(
            model="omni-moderation-latest",
            input=response,
        )

        output_moderated_response = output_moderation.results[0]

        if output_moderated_response.flagged:
            return jsonify({"message": default_output_response}), 200

        response = result["message"]
        
        if user_message.strip():  # Only add user message if it's not empty
            session['dashboard_history'].append({'HumanMessage': user_message})
        session['dashboard_history'].append({'AIMessage': response})

        # Trimming history to prevent session overflow (keeping it at last 20 messages)
        if len(session['dashboard_history']) > 20:
            session['dashboard_history'] = session['dashboard_history'][-20:]

        #Mark session as modified to ensure it saves
        session.modified = True

        print(f"RESPONSE: New history length={len(session['dashboard_history'])}")

        """return jsonify({
            'message': response,
            'dialogue': session['dashboard_history']  #Return history to frontend
        }), 200"""

        return jsonify({
            'message': response
        }), 200
        
    except Exception as e:
        print(f"FULL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Error occurred'}), 500

@app.route('/tutoring', methods = ['POST'])
def tutoring():
    try:
        data = request.get_json()
        user_message = data.get('message')

        default_input_response = "A message sent to the tutor has been flagged unsafe and cannot be processed. Please ensure that any message sent does elicit or include harmful content spanning harassment, hate speech, illicit activities, self-harm, sexual content or violence "
        default_output_response = "A message from the tutor been flagged as unsafe and cannot be processed. Please resend you previous message to continue the tutoring session."


        client = OpenAI()

        input_moderation = client.moderations.create(
            model="omni-moderation-latest",
            input= user_message,
        )

        input_moderated_response = input_moderation.results[0]

        if input_moderated_response.flagged:
            return jsonify({"message": default_input_response}), 200


        #study_meterial = retrieveData()
        skill_components = retrieveData()
        knowledgeStateData = skill_components.get_skill_components(session['user_id'])

        print(session["current_state"], "-------attempts in main.py before state")

        state = {
            "username": session['username'],
            "user_id": session['user_id'],
            "user_message": user_message,
            "history": session['tutoring_history'],
            "skill_component": knowledgeStateData,
            "attempts": session['attempts'],
            "current_state": session['current_state'],
            "current_question": session.get('question', ''),
            "current_tutor_message": session.get('current_tutor_message', ''),
            "target_skill": session.get('target_skill', ''),
        }

        graph_builder = tutor_graph()

        result = graph_builder.invoke(state)

        # Create compState object from the result
        my_obj = mainState(**result)
        
        #print("Pydantic object created successfully______", my_obj)
        print("Final mark______", result.get('mark', 'No mark returned'))
            
        response = my_obj.ai_response

        # Guard: if ai_response is None or not a string, something went wrong upstream
        if not response or not isinstance(response, str):
            print("WARNING: ai_response is None or invalid, cannot continue")
            return jsonify({'message': 'The tutor could not generate a response, please try again.'}), 200

        # In main.py around line 293, replace the session updates with:
        session['attempts'] = result.get('attempts', 0) if result.get('attempts', 0) < 5 else 0
        session['current_state'] = result.get('current_state') if result.get('current_state') is not None else session['current_state']
        session['question'] = result.get('current_question') if result.get('current_question') is not None else session.get('question', '')
        session['target_skill'] = result.get('target_skill') if result.get('target_skill') is not None else session.get('target_skill', '')
        session.modified = True
        output_moderation = client.moderations.create(
            model="omni-moderation-latest",
            input=response,
        )

        output_moderated_response = output_moderation.results[0]

        if output_moderated_response.flagged:
            #uncomment for debugging
            """for category, is_flagged in output_moderated_response.categories.model_dump().items():
                if is_flagged:
                    # Get the score for this category
                    score = getattr(output_moderated_response.category_scores, category.replace('/', '_'))
                    print(f"  - {category}: {score:.4f}")"""
            return jsonify({"message": default_output_response}), 200
            
        return jsonify({"message": response}), 200
    
    except Exception as e:
        print(f"FULL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Error occurred'}), 500
    
##################################################################
##########   Handle Simple Routes
#################################################################
@app.route('/')
def home():
    return render_template('main.html')

@app.route('/another-page')
def another_page():
    return render_template('upload.html')

@app.route('/study', methods = ['GET'])
def study():
    if 'user_id' in session:
        return render_template('study.html')
    else:
        return render_template('main.html'), 401

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)