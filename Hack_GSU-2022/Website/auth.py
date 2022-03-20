from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, UPLOAD_FOLDER
from flask_login import login_user, login_required, logout_user, current_user

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email=request.form.get('email')
        password=request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                flash('Logged in Successfully', category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.home'))
            else:
                flash('Incorrect password, try again', category='error')
        else:
            flash('Email does not exist', category='error')

    return render_template("login.html", user=current_user)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists', category='error')
        elif len(email) < 4:
            flash('Email must be greater than 3 characters', category='error')
        # elif len(first_name) < 2:
        #     flash('First name should be grater than 2 characters', category='error')
        elif password1 != password2:
            flash('Passwords dont Match', category='error')
        elif len(password1) < 7:
            flash('Password shoud be at least 7 characters', category='error')
        else:
            new_user = User(email=email, first_name=first_name, password=generate_password_hash(password1, method='sha256'))
            db.session.add(new_user)
            db.session.commit()
            flash('Account Created!', category='error')
            # login_user(user, remember=True)
            return redirect(url_for('views.home'))

    return render_template("sign_up.html", user=current_user)

@auth.route('/about')
def about():
    return render_template("about.html", user=current_user)

@auth.route('/contact')
def contact():
    return render_template("contact.html", user=current_user)

@auth.route('/upload', methods=['GET', 'POST'])
@login_required
def uploads():
    def transform(text_content, entities):
        '''adds hyperlinks to text'''
        import re
        
        for entity in entities:
            wiki = entity['wiki']
            for mention in entity['mentions']:
                if mention != 'candidate':
                    text_content = re.sub(mention+'(?![<"_])', f'<a href="{wiki}">{mention}</a>', text_content)

        text_content = re.sub(r'\n', '<br>', text_content)
        return(text_content)

    def analyze(text_content):
        '''çalls the google entity recognition api returns entities in text with a wiki page'''
        from google.cloud import language_v1
        
        client = language_v1.LanguageServiceClient()

        # Available types: PLAIN_TEXT, HTML
        type_ = language_v1.Document.Type.PLAIN_TEXT

        document = {"content": text_content, "type_": type_}

        encoding_type = language_v1.EncodingType.UTF8

        response = client.analyze_entities(request = {'document': document, 'encoding_type': encoding_type})

        # Loop through entitites returned from the API
        entities = []
        for entity in response.entities:
            for metadata_name, metadata_value in entity.metadata.items():
                if metadata_name == 'wikipedia_url':
                    wiki = metadata_value
                    break
            else:
                wiki = False
            # append entities with a wiki page to list
            if wiki:
                entities.append({'wiki': wiki, 
                                'mentions': set([mention.text.content for mention in entity.mentions])})

        return entities
        
    def convert_pdf(file_path):
        '''turn pdf into plaintext'''
        from io import StringIO

        from pdfminer.converter import TextConverter
        from pdfminer.layout import LAParams
        from pdfminer.pdfdocument import PDFDocument
        from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
        from pdfminer.pdfpage import PDFPage
        from pdfminer.pdfparser import PDFParser

        output_string = StringIO()
        with open(file_path, 'rb') as in_file:
            parser = PDFParser(in_file)
            doc = PDFDocument(parser)
            rsrcmgr = PDFResourceManager()
            device = TextConverter(rsrcmgr, output_string, laparams=LAParams())
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            for page in PDFPage.create_pages(doc):
                interpreter.process_page(page)

        return(output_string.getvalue())

    import os
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\SemKj\Downloads\skilful-nexus-344522-3d57dd4a3fa9.json"

    from werkzeug.utils import secure_filename
    file = request.files['file']
    filename = secure_filename(file.filename)
    file.save(filename)
    plaintext = convert_pdf(filename)
    entities = analyze(plaintext)
    output_text = transform(plaintext, entities)
    os.remove(filename)
    print(output_text)
    return render_template("uploads.html", user=current_user, text=output_text)

