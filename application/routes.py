import requests as req
from flask import render_template, url_for, flash, redirect, request, abort, jsonify
from application import app, db, bcrypt, mail
from application.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm, CommentForm, RequestResetForm, ResetPasswordForm, AnswerCommentForm
from application.models import User, Post, Answer, Comment, Vote, Downvote, Tags, tagposts, Answerupvotes, Answerdownvotes, Favourite, AnswerComment
from flask_login import login_user, current_user, logout_user, login_required
import secrets
import os
import sqlite3
from PIL import Image
from sqlalchemy.sql import exists
from sqlalchemy import func
from sqlalchemy import and_, or_
from sqlalchemy import create_engine
import json
from flask_mail import Message



def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def create_connection(db_file):
    try:
        conn = sqlite3.connect("application/" + db_file, isolation_level=None)
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        return cursor

    except Exception as e:
        print(e)



# ---------- Home route ---------
@app.route("/")
@app.route("/home")
def home():
    page = request.args.get('page',1,type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    # print(Post.query.order_by(Post.date_posted.desc()).all())

    # Join tables (tagposts, Tags and Post) to get tags for each post
    joinedTables = db.session.query(tagposts.post_id,tagposts.tag_id,Tags.tag_title,Post.title,Post.user_id,Post.like_count,Post.content).join(Tags).join(Post).all()

    recommended_items_default = []
    items = db.session.query(Post).order_by(Post.date_posted.desc()).all()
    if not items:
        recommended_items_default.clear()

    else:
        for x in items:
            recommended_items_default.append(x.id)
        print('default', recommended_items_default)

    if current_user.is_authenticated:
        print('in auth')
        uid = current_user.id
        print('uid: ', uid)
         # API call
        furl = "http://mayankms02.pythonanywhere.com/api/sCLAzIJDKmi1SfWLeapXYA/data_delivery/tag_item"
        params = {"uid": uid}
        response = req.post(furl,params=params)
        if str(response) == '<Response [200]>':
            print(response.text)
            print('resp 200')

            recommended_items = json.loads(response.text)
            if not recommended_items:
                flash("No posts on the site, Add a post to start!", 'info')
                return redirect('/post/new')

            else:
                return render_template('home.html', posts=posts, joinedTables=joinedTables, recommended_items=recommended_items)
        else:
            print(response)
            # return jsonify("error")
            return render_template('home.html', posts=posts, recommended_items=recommended_items_default, joinedTables=joinedTables)


    else:
        return render_template('home.html', posts=posts, recommended_items=recommended_items_default, joinedTables=joinedTables)

# ---------- Local Feed route ---------
@app.route("/personal")
def personal():
    page = request.args.get('page',1,type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)

    # Join tables (tagposts, Tags and Post) to get tags for each post
    joinedTables = db.session.query(tagposts.post_id,tagposts.tag_id,Tags.tag_title,Post.title,Post.user_id,Post.like_count,Post.content).join(Tags).join(Post).all()

    if current_user.is_authenticated:
        uid = current_user.id

        # API call
        furl = "http://mayankms02.pythonanywhere.com/api/sCLAzIJDKmi1SfWLeapXYA/data_delivery/tag_item"
        params = {"uid": uid}
        response = req.post(furl,params=params)
        if str(response) == '<Response [200]>':
            resp = ""
            for x in response.text :
                if x == '[' or x == ']' or x == " " or x == '\n':
                    continue
                else:
                    resp += x
            recommended_items = resp.split(',')
            int_recommended_list = []
            for x in recommended_items:
                int_recommended_list.append(int(x))
            print(int_recommended_list)
            for x in recommended_items:

                post = db.session.query(Post).filter_by(id=x).all()
                print(x)
                print(post)


                # post = db.session.query(Post).all()
                return render_template('personal.html', posts=posts, joinedTables=joinedTables, post=post, recommended_items=int_recommended_list)

# ---------- Register route ---------
@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()

        email = form.email.data
        storedUser = db.session.query(User).filter(User.email==email).all()
        print(storedUser)
        send_verification_email(user)
        flash('An email has been sent with instructions to verify your password.', 'info')
       


        # API call
        furl = "http://mayankms02.pythonanywhere.com/api/sCLAzIJDKmi1SfWLeapXYA/data_entry/registered_users"
        dbase = create_connection('site.db')
        sql = 'select * from User where username = "{}"'.format(form.username.data)
        try:
            user = dbase.execute(sql).fetchall()
        except Exception as e:
            print(e)
        uid = user[0]['id']
        params = {"uid": uid}
        response = req.post(furl,params=params)
        if str(response) == '<Response [200]>':
            # flash('Your account has been created! You are now able to log in', 'success')
            return redirect(url_for('login'))
        else:
            print('api call error')
            return redirect(url_for('login'))

    #     return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

# ---------- Login route ---------
@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and bcrypt.check_password_hash(user.password, form.password.data) and user.verified == 1:
            login_user(user, remember=form.remember.data)
            flash('You have been logged in!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
            return redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password or verify your email', 'danger')
    return render_template('login.html', title='Login', form=form)

# ---------- Logout route ---------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

def send_reset_email(user):
    if user is None:
        return redirect(url_for('login'))

    else:   
        token = user.get_reset_token()
        msg = Message('Password Reset Request',
                    sender='noreply@demo.com',
                    recipients=[user.email])
        msg.body = f'''To reset your password, visit the following link:
    {url_for('reset_token', token=token, _external=True)}
    If you did not make this request then simply ignore this email and no changes will be made.
    '''
        mail.send(msg)

def send_verification_email(user):
    token = user.get_reset_token()
    msg = Message('Email verification',
                  sender='noreply@demo.com',
                  recipients=[user.email])
    msg.body = f'''To verify your email, visit the following link:
{url_for('verify_token', token=token, _external=True)}
If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)

# ---------- Reset Password route ---------
@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)

# ---------- Reset Paasword Token route ---------
@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
            return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('Invalid or Expired Token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Passwords', form=form)

# ---------- Verify Email Token route ---------
@app.route("/verify_email/<token>", methods=['GET', 'POST'])
def verify_token(token):
    if current_user.is_authenticated:
            return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('Invalid or Expired Token', 'warning')
        return redirect(url_for('login'))

    user.verified = 1
    db.session.commit()

    flash('Your email has been verified', 'success')
    return redirect(url_for('login'))
    



# ---------- Save picture method ---------
def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125,125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    # form_picture.save(picture_path)
    return picture_fn

# ---------- Account route ---------
@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file

        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash("Your account has been updated", 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data  = current_user.username
        form.email.data = current_user.email

    image_file = url_for('static', filename='profile_pics/'+ current_user.image_file)
    return render_template('account.html', title='Account', image_file=image_file, form=form)
     
# ---------- New Post route ---------
@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        post = Post(title=request.form.get('title'), content=request.form.get('content'), author=current_user)
        db.session.add(post)
        db.session.commit()
        taglist = []
        # Get all tags on the post
        many_tags = request.form.getlist('tags')
        # print(len(many_tags))

        for one_tag in many_tags:
            # print(one_tag)

            # check if tag is  present in table
            tag_present = db.session.query(db.exists().where(and_(Tags.tag_title == one_tag))).scalar()
            if tag_present:
                tag_row = db.session.query(Tags).filter_by(tag_title=one_tag).all()
                # tagid of old tags in a taglist
                for item in tag_row:
                    taglist.append(item.tag_id)
            else:
                tag = Tags(tag_title=one_tag)
                db.session.add(tag)
                db.session.commit()
                tag_row = db.session.query(Tags).filter_by(tag_title=one_tag).all()
                for item in tag_row:
                    taglist.append(item.tag_id)
        print("taglist: ", taglist)
        # flash("Your question has been posted","success")

        recent_post = Post.query.order_by(Post.date_posted.desc()).first()
        post_id = recent_post.id



        for tag in taglist:
            something = tagposts(post_id=post_id, tag_id=tag)
            db.session.add(something)
            db.session.commit()

        # API Call
        furl = "http://mayankms02.pythonanywhere.com/api/sCLAzIJDKmi1SfWLeapXYA/data_entry/item_tags"
        params = {"uid": current_user.id, "itemid": post_id, "taglist": taglist}
        print('params: ', params)
        response = req.post(furl,params=params)
        if str(response) == '<Response [200]>':
            flash("Your post has been added", 'success')
            return redirect(url_for('home'))
        else:
            print('api call error')
            return redirect(url_for('home'))

    elif request.method == 'GET':
        dbase = create_connection("site.db")
        sql = 'select * from Tags'
        try:
            taglist = dbase.execute(sql).fetchall()
        except Exception as e:
            print(e)
        return render_template('create_post.html', title='Ask Question', legend='Ask Question', taglist=taglist)


# ---------- Posts route ---------
@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html',title=post.title,post=post)

# ---------- Update Post route ---------
@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    # Join tables (tagposts, Tags and Post) to get tags for each post
    joinedTables = db.session.query(tagposts.post_id,tagposts.tag_id,Tags.tag_title,Post.title,Post.user_id,Post.like_count,Post.content).join(Tags).join(Post).all()


    post_dict = dict()
    post_dict['post_id'] = post_id
    post_dict['post_title'] = post.title
    post_dict['post_content'] = post.content

    if request.method == 'POST':
        post.title = request.form.get('title')
        post.content = request.form.get('content')
        db.session.commit()
        taglist = []

        # Get all tags on the post
        many_tags = request.form.getlist('tags')
        for one_tag in many_tags:
            # check if tag is  present in table
            tag_present = db.session.query(db.exists().where(and_(Tags.tag_title == one_tag))).scalar()
            if tag_present:
                tag_row = db.session.query(Tags).filter_by(tag_title=one_tag).all()
                # tagid of old tags in a taglist
                for item in tag_row:
                    taglist.append(item.tag_id)
            else:
                tag = Tags(tag_title=one_tag)
                db.session.add(tag)
                db.session.commit()
                tag_row = db.session.query(Tags).filter_by(tag_title=one_tag).all()
                for item in tag_row:
                    taglist.append(item.tag_id)
        print("taglist: ", taglist)

        for tag in taglist:
            tag_in_tagposts = db.session.query(db.exists().where(and_(tagposts.post_id == post_id, tagposts.tag_id == tag))).scalar()
            if not tag_in_tagposts:
                something = tagposts(post_id=post_id, tag_id=tag)
                db.session.add(something)
                db.session.commit()

        tagpost_post_rows = db.session.query(tagposts).filter_by(post_id=post_id).all()
        already_in_tagpost = []
        for x in tagpost_post_rows:
            already_in_tagpost.append(x.tag_id)
        print(already_in_tagpost)
        for x in already_in_tagpost:
            if x not in taglist:
                delete_from_tagposts = tagposts.query.filter_by(tag_id=x).delete()
                db.session.commit()


        return redirect(url_for('comment_post', post_id=post_id))

    # Populate form with current post data
    elif request.method == 'GET':

        dbase = create_connection("site.db")
        sql = 'select * from Tags'
        try:
            taglist_rows = dbase.execute(sql).fetchall()
        except Exception as e:
            print(e)
        taglist = []
        for x in taglist_rows:
            taglist.append(x['tag_title'])
        
        sql = 'select * from tagposts where post_id = {}'.format(post_id)
        try:
            tagposts_rows = dbase.execute(sql).fetchall()
        except Exception as e:
            print(str(e))
        pre_tag_id = []
        for x in tagposts_rows:
            pre_tag_id.append(x['tag_id'])
        print('pre_tg: ', pre_tag_id)
        tags = []
        for y in taglist_rows:
            if y['tag_id'] in pre_tag_id:
                tags.append(y['tag_title'])
        print('selected: ', tags)
        print('all tags: ', taglist)

        for x in tags:
            print('next iteration', x)
            if x in taglist:
                print('x: ', x)
                taglist.remove(x)



        
        
        return render_template('update.html', post=post_dict, joinedTables=joinedTables, title='Update Post', legend='Edit Your Question', taglist=taglist, tags=tags)

# ---------- Delete Post route ---------
@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    Favourite.query.filter_by(post_id=post_id).delete()
    db.session.commit()
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()

    # API call
    furl = "http://mayankms02.pythonanywhere.com/api/sCLAzIJDKmi1SfWLeapXYA/data_deletion/delete_item"
    params = {"itemid": post_id}
    response = req.post(furl,params=params)
    if str(response) == '<Response [200]>':
        print("Item is deleted successfuly")

    flash('Your question has been deleted', 'success')
    return redirect(url_for('home'))

# ---------- User Posts route ---------
@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user)\
        .order_by(Post.date_posted.desc())\
        .paginate(page=page, per_page=5)

    # Join tables (tagposts, Tags and Post) to get tags for each post
    joinedTables = db.session.query(tagposts.post_id,tagposts.tag_id,Tags.tag_title,Post.title,Post.user_id,Post.like_count,Post.content).join(Tags).join(Post).all()

    return render_template('user_posts.html', posts=posts, user=user, joinedTables=joinedTables)

# ---------- Post Comment route ---------
@app.route("/post/<int:post_id>/comment", methods=['GET', 'POST'])
@login_required
def comment_post(post_id):
    post = Post.query.get_or_404(post_id)
    posts_id = post.id
    
    # Join tables (tagposts, Tags and Post) to get tags for each post
    joinedTables = db.session.query(tagposts.post_id,tagposts.tag_id,Tags.tag_title,Post.title,Post.user_id,Post.like_count,Post.content).join(Tags).join(Post).all()

    # Get answersCount on post
    answersCount = db.session.query(Answer).filter(Answer.post_id == post_id).count()

    # Get all answers from Answer table
    answers = Answer.query.order_by(Answer.like_count.desc()).all()

    if request.method == 'POST':
        comment = Comment(comment=request.form.get('comment'), post_id=posts_id, user_id=current_user.id)
        post = Post.query.get_or_404(post_id)
        db.session.add(comment)
        db.session.commit()
        print(current_user.id)
        comments = Comment.query.filter(Comment.post_id == post_id).order_by(Comment.date_posted.desc())
        flash('Your comment has been added', 'success')

        return render_template('comment_post.html', title='Comments', post=post, comments=comments, joinedTables=joinedTables, answersCount=answersCount, answers=answers)

    if request.method =='GET':
        comments = Comment.query.filter(Comment.post_id == post_id).order_by(Comment.date_posted.desc())
        return render_template('comment_post.html', title='Comments', post=post, comments=comments, joinedTables=joinedTables, answersCount=answersCount, answers=answers)

# ---------- Edit Post Comment route ---------
@app.route("/post/<int:post_id>/comment/<int:comment_id>/update", methods=['GET','POST'])
@login_required
def updateComment(post_id, comment_id):
    comment = Comment.query.get_or_404(comment_id)
    post_id = post_id
    comment.comment = request.form.get('comment')
    db.session.commit()
   
    comments = Comment.query.filter(Comment.post_id == post_id).order_by(Comment.date_posted.desc())
    flash('Your comment has been updated', 'success')

    return redirect(url_for('comment_post', post_id=post_id))





# ---------- Search route ---------
@app.route("/search", methods=['GET', 'POST'])
def search():
        page = request.args.get('page', 1, type=int)
        searched_content = request.form.get('search')
        search_word_list = searched_content.split(" ")
        print(search_word_list)

        # Join tables (tagposts, Tags and Post) to get tags for each post
        joinedTables = db.session.query(tagposts.post_id,tagposts.tag_id,Tags.tag_title,Post.title,Post.user_id,Post.like_count,Post.content).join(Tags).join(Post).all()
      
        searched_posts = []
        searched_post_a = []
        for word in search_word_list:

            searched_post_a = Post.query.filter(or_(Post.title.like('%'+word+'%'),Post.content.like('%'+searched_content+'%'))).all()
            
            for x in searched_post_a:
                if x not in searched_posts:
                    searched_posts.append(x)

        print('searched: ', searched_posts)
        return render_template('search.html', searched_posts=searched_posts, query=searched_content, joinedTables=joinedTables)

# ---------- Upvote route ---------
@app.route('/vote/<int:post_id>/<int:user_id>')
@login_required
def upvote(post_id,user_id):
    posts = Post.query.get_or_404(post_id)

    # Check if entry is already present in the table
    post_present = db.session.query(db.exists().where(and_(Vote.post_id == post_id, Vote.user_id == user_id))).scalar()

    # Check if user has Disliked this post or not
    post_inDownvote = db.session.query(db.exists().where(and_(Downvote.post_id == post_id, Downvote.user_id == user_id))).scalar()


    if post_present == True:
        print("All ready upvoted")
        print(post_id)
        print(user_id)
        print(post_present)

        # If Yes, Delete the entry
        Vote.query.filter_by(post_id=post_id, user_id=user_id).delete()
        db.session.commit()

        # API call
        furl = "https://mayankms02.pythonanywhere.com/api/sCLAzIJDKmi1SfWLeapXYA/data_entry/user_action"
        params = {"uid": user_id, "itemid": post_id, "action": 0}
        response = req.post(furl,params=params)
        if str(response) == '<Response [200]>':
            print('API call successful')

        # Count all entries on that post
        upvoteCount = db.session.query(Vote).filter(Vote.post_id == post_id).count()
        posts.like_count = upvoteCount
        db.session.commit()

        print(posts.like_count)
        print(posts)
        print("inside if")

        upvote = db.session.query(Vote).filter(Vote.post_id == post_id).count()
        downvote = db.session.query(Downvote).filter(Downvote.post_id == post_id).count()

        vote_data = {'vote_count': upvote, 'downvote_count': downvote}
        print('vote_data', vote_data)
        return jsonify(vote_data)


        # If entry is not already present in the table
    elif post_inDownvote == True:
        Downvote.query.filter_by(post_id=post_id, user_id=user_id).delete()
        print("Dislike Removed")
        db.session.commit()
        # Then add entry in the table
        vote = Vote(user_id=user_id, post_id=post_id)
        vote.action = 1
        db.session.add(vote)
        db.session.commit()

        # API call
        furl = "https://mayankms02.pythonanywhere.com/api/sCLAzIJDKmi1SfWLeapXYA/data_entry/user_action"
        params = {"uid": user_id, "itemid": post_id, "action": 1}
        response = req.post(furl,params=params)
        if str(response) == '<Response [200]>':
            print('API call successful')

        # Count all entries on that post
        upvoteCount = db.session.query(Vote).filter(Vote.post_id == post_id).count()
        posts.like_count = upvoteCount
        db.session.commit()

        downvoteCount = db.session.query(Downvote).filter(Downvote.post_id == post_id).count()
        posts.dislike_count = downvoteCount
        db.session.commit()

        print(db.session.query(Vote).filter(Vote.post_id == post_id).count())
        print(posts.like_count)
        print(posts)
        print("inside elif")
        upvote = db.session.query(Vote).filter(Vote.post_id == post_id).count()
        downvote = db.session.query(Downvote).filter(Downvote.post_id == post_id).count()

        vote_data = {'vote_count': upvote, 'downvote_count': downvote}
        print('vote_data', vote_data)
        return jsonify(vote_data)
    else:
        # Then add entry in the table
        vote = Vote(user_id=user_id, post_id=post_id)
        vote.action = 1
        db.session.add(vote)
        db.session.commit()

        # API call
        furl = "https://mayankms02.pythonanywhere.com/api/sCLAzIJDKmi1SfWLeapXYA/data_entry/user_action"
        params = {"uid": user_id, "itemid": post_id, "action": 1}
        response = req.post(furl,params=params)
        if str(response) == '<Response [200]>':
            print('API call successful')

        # Count all entries on that post
        upvoteCount = db.session.query(Vote).filter(Vote.post_id == post_id).count()
        posts.like_count = upvoteCount
        db.session.commit()

        print(db.session.query(Vote).filter(Vote.post_id == post_id).count())
        print(posts.like_count)
        print(posts)
        print("inside else")
        upvote = db.session.query(Vote).filter(Vote.post_id == post_id).count()
        downvote = db.session.query(Downvote).filter(Downvote.post_id == post_id).count()

        vote_data = {'vote_count': upvote, 'downvote_count': downvote}
        print('vote_data', vote_data)
        return jsonify(vote_data)


# ---------- Downvote route ---------
@app.route('/downvote/<int:post_id>/<int:user_id>')
@login_required
def downvote(post_id,user_id):
    posts = Post.query.get_or_404(post_id)

    # Check if entry is already present in the table
    post_present = db.session.query(db.exists().where(and_(Downvote.post_id == post_id, Downvote.user_id == user_id))).scalar()

    # Check if user has Liked this post or not
    post_inVote = db.session.query(db.exists().where(and_(Vote.post_id == post_id, Vote.user_id == user_id))).scalar()

    if post_present == True:
        print("All ready downvoted")
        print(post_present)

        # If YES, Delete the entry
        Downvote.query.filter_by(post_id=post_id, user_id=user_id).delete()
        db.session.commit()

        # API call
        furl = "https://mayankms02.pythonanywhere.com/api/sCLAzIJDKmi1SfWLeapXYA/data_entry/user_action"
        params = {"uid": user_id, "itemid": post_id, "action": 0}
        response = req.post(furl,params=params)
        if str(response) == '<Response [200]>':
            print('API call successful')

        # Count all entries on that post
        DownvoteCount = db.session.query(Downvote).filter(Downvote.post_id == post_id).count()
        posts.dislike_count = DownvoteCount
        db.session.commit()

        upvote = db.session.query(Vote).filter(Vote.post_id == post_id).count()
        downvote = db.session.query(Downvote).filter(Downvote.post_id == post_id).count()

        vote_data = {'vote_count': upvote, 'downvote_count': downvote}
        print('vote_data', vote_data)
        return jsonify(vote_data)

    # If entry is not already present in the table
    elif post_inVote == True:
        # Remove like on the post from Vote table
        Vote.query.filter_by(post_id=post_id, user_id=user_id).delete()
        print("Like Removed")
        db.session.commit()
        # Then add entry in the table
        downvote = Downvote(user_id=user_id, post_id=post_id)
        downvote.action = "disliked"
        db.session.add(downvote)
        db.session.commit()


        # API call
        furl = "https://mayankms02.pythonanywhere.com/api/sCLAzIJDKmi1SfWLeapXYA/data_entry/user_action"
        params = {"uid": user_id, "itemid": post_id, "action": -1}
        response = req.post(furl,params=params)
        if str(response) == '<Response [200]>':
            print('API call successful')

        # Count all entries on that post
        downvoteCount = db.session.query(Downvote).filter(Downvote.post_id == post_id).count()
        posts.dislike_count = downvoteCount
        db.session.commit()

        upvoteCount = db.session.query(Vote).filter(Vote.post_id == post_id).count()
        posts.like_count = upvoteCount
        db.session.commit()

        print(db.session.query(Downvote).filter(Downvote.post_id == post_id).count())
        print(posts.dislike_count)
        print(posts)
        print("inside elif")
        upvote = db.session.query(Vote).filter(Vote.post_id == post_id).count()
        downvote = db.session.query(Downvote).filter(Downvote.post_id == post_id).count()

        vote_data = {'vote_count': upvote, 'downvote_count': downvote}
        print('vote_data', vote_data)
        return jsonify(vote_data)

    else:
        # Then add entry in the table
        downvote = Downvote(user_id=user_id, post_id=post_id)
        downvote.action = -1
        db.session.add(downvote)
        db.session.commit()

        # API call
        furl = "https://mayankms02.pythonanywhere.com/api/sCLAzIJDKmi1SfWLeapXYA/data_entry/user_action"
        params = {"uid": user_id, "itemid": post_id, "action": -1}
        response = req.post(furl,params=params)
        if str(response) == '<Response [200]>':
            print('API call successful')

        # Count all entries on that post
        downvoteCount = db.session.query(Downvote).filter(Downvote.post_id == post_id).count()
        posts.dislike_count = downvoteCount
        db.session.commit()
        upvote = db.session.query(Vote).filter(Vote.post_id == post_id).count()
        downvote = db.session.query(Downvote).filter(Downvote.post_id == post_id).count()

        vote_data = {'vote_count': upvote, 'downvote_count': downvote}
        print('vote_data', vote_data)
        return jsonify(vote_data)


# ---------- Tags route ---------
@app.route('/tags/<tag_title>')
def tags(tag_title):
    page = request.args.get('page',1,type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    tag_title = tag_title

    # Join tables (tagposts, Tags and Post) to get tags for each post
    joinedTables = db.session.query(tagposts.post_id,tagposts.tag_id,Tags.tag_title,Post.title,Post.id,Post.user_id,Post.like_count, Post.dislike_count,Post.content,Post.author,Post.date_posted,User.username,User.image_file).join(Tags).join(Post).join(User).all()

    required_posts_and_tags = []
    for item in joinedTables:
        if tag_title == item.tag_title:
            post_ki_id = item.id
            dbase = create_connection('site.db')
            sql = 'SELECT tagposts.post_id AS tagposts_post_id, tagposts.tag_id AS tagposts_tag_id,\
                tags.tag_title AS tags_tag_title FROM tagposts JOIN tags ON tags.tag_id = tagposts.tag_id WHERE \
                tagposts.post_id ={}'.format(post_ki_id)
            try:
                tags_on_post = dbase.execute(sql).fetchall()
            except Exception as e:
                print(str(e)) 

            for a in tags_on_post:
                required_posts_and_tags.append(a)

    return render_template("tags.html", posts=posts, joinedTables=joinedTables, tag_title=tag_title, list_of_all_post_tags=required_posts_and_tags)

# ---------- Delete Comment route ---------
@app.route("/post/<post_id>/comment/<comment_id>/delete", methods=['POST'])
@login_required
def delete_comment(post_id,comment_id):
    if request.method == 'POST':
        
        comment_exists = db.session.query(db.exists().where(and_(Comment.post_id == post_id, Comment.comment_id == comment_id))).scalar()
        print(comment_exists)
        if comment_exists:
            comment = Comment.query.get(comment_id)
            print(comment)
            post = Post.query.get(post_id)
            print(post)
            if post.author != current_user:
                return jsonify(False)
            db.session.delete(comment)
            db.session.commit()
            flash('Comment has been deleted', 'success')
            return jsonify(True)

# ---------- Answer route ---------
@app.route("/answer/<int:post_id>", methods=['GET', 'POST'])
@login_required
def answer(post_id):
    if request.method == 'POST':
        answer = Answer(content=request.form.get('editordata'), author=current_user, post_id=post_id)
        db.session.add(answer)
        db.session.commit()

        post = Post.query.get_or_404(post_id)
        posts_id = post.id

        return redirect(url_for('comment_post', post_id=post_id))

    return redirect(url_for('comment_post', post_id=post_id))

# ---------- Delete Answer route ---------
@app.route("/answer/<int:answer_id>/delete", methods=['POST'])
@login_required
def delete_answer(answer_id):
    print(answer_id)
    answer = Answer.query.get_or_404(answer_id)
    post_id = answer.post_id
    print('and.auth', answer.author)
    print('curr.user', current_user)
    if answer.author != current_user:
        abort(403)
    db.session.delete(answer)
    db.session.commit()
    flash('Your answer has been deleted', 'success')
    return jsonify(True)

# ---------- Answer Comment route ---------
@app.route("/answer/<int:answer_id>/comment", methods=['GET', 'POST'])
@login_required
def answercomment(answer_id):
    answer = Answer.query.get_or_404(answer_id)
    answer_id = answer.id
    print(answer)

    form = AnswerCommentForm()
    if form.validate_on_submit():
        comment = AnswerComment(comment=form.comment.data, answer_id=answer_id, user_id=current_user.id)
        answer = Answer.query.get_or_404(answer_id)
        db.session.add(comment)
        db.session.commit()
        comments = AnswerComment.query.filter(AnswerComment.answer_id == answer_id).all()

        return render_template('answer_comment.html', title='Comments', form=form, comments=comments, answer=answer)
    else:
        comments = AnswerComment.query.filter(AnswerComment.answer_id == answer_id).all()
        return render_template('answer_comment.html', title='Comments', form=form, comments=comments, answer=answer)


# ---------- Mostliked route ---------
@app.route('/most_liked')
def most_liked():
    page = request.args.get('page',1,type=int)
    posts = Post.query.order_by(Post.like_count.desc()).paginate(page=page, per_page=5)
    voted = Vote.query.order_by(Vote.post_id.desc())

    # Join tables (tagposts, Tags and Post) to get tags for each post
    joinedTables = db.session.query(tagposts.post_id,tagposts.tag_id,Tags.tag_title,Post.title,Post.user_id,Post.like_count,Post.content).join(Tags).join(Post).all()
    # print(joinedTables)


    return render_template('most_liked.html', posts=posts, voted=voted, joinedTables=joinedTables)

# ---------- Answer Upvotes route ---------
@app.route('/AnswerUpvotes/<int:answer_id>/<int:user_id>')
@login_required
def answerLikes(answer_id,user_id):
    answers = Answer.query.get_or_404(answer_id)
    print(answers)

    # Check if entry is already present in the table
    answer_present = db.session.query(db.exists().where(and_(Answerupvotes.answer_id == answer_id, Answerupvotes.user_id == user_id))).scalar()
    # Check if user has Disliked this post or not
    post_inAnswerDownvote = db.session.query(db.exists().where(and_(Answerdownvotes.answer_id == answer_id, Answerdownvotes.user_id == user_id))).scalar()


    if answer_present == True:
        print("All ready upvoted")
        print(answer_id)
        print(user_id)
        print(answer_present)

        # If Yes, Delete the entry
        Answerupvotes.query.filter_by(answer_id=answer_id, user_id=user_id).delete()
        Answerupvotes.action = "not-liked"
        db.session.commit()
        # flash("Your vote has been removed.","success")

        # Count all entries on that post
        upvoteCount = db.session.query(Answerupvotes).filter(Answerupvotes.answer_id == answer_id).count()
        answers.like_count = upvoteCount
        db.session.commit()
        print(db.session.query(Answerupvotes).filter(Answerupvotes.answer_id == answer_id).count())
        print(answers.like_count)
        print(answers)
        print("inside if")

        upvote = db.session.query(Answerupvotes).filter(Answerupvotes.answer_id == answer_id).count()
        downvote = db.session.query(Answerdownvotes).filter(Answerdownvotes.answer_id == answer_id).count()

        vote_data = {'vote_count': upvote, 'downvote_count': downvote}
        print('vote_data', vote_data)
        return jsonify(vote_data)


        # If entry is not already present in the table
    elif post_inAnswerDownvote == True:
        Answerdownvotes.query.filter_by(answer_id=answer_id, user_id=user_id).delete()
        print("Dislike Removed")
        db.session.commit()

        # Then add entry in the table
        answersUpvote = Answerupvotes(user_id=user_id, answer_id=answer_id)
        answersUpvote.action = "liked"
        db.session.add(answersUpvote)
        db.session.commit()
        # flash("Your vote has been registered.","success")
        print(post_inAnswerDownvote)

        # Count all entries on that post
        upvoteCount = db.session.query(Answerupvotes).filter(Answerupvotes.answer_id == answer_id).count()
        answers.like_count = upvoteCount
        db.session.commit()

        downvoteCount = db.session.query(Answerdownvotes).filter(Answerdownvotes.answer_id == answer_id).count()
        answers.dislike_count = downvoteCount
        db.session.commit()

        print(db.session.query(Answerupvotes).filter(Answerupvotes.answer_id == answer_id).count())
        print(answers.like_count)
        print(answers)
        print("inside elif")

        upvote = db.session.query(Answerupvotes).filter(Answerupvotes.answer_id == answer_id).count()
        downvote = db.session.query(Answerdownvotes).filter(Answerdownvotes.answer_id == answer_id).count()

        vote_data = {'vote_count': upvote, 'downvote_count': downvote}
        print('vote_data', vote_data)
        return jsonify(vote_data)
    else:
        # Then add entry in the table
        answerUpvotes = Answerupvotes(user_id=user_id, answer_id=answer_id)
        answerUpvotes.action = "liked"
        db.session.add(answerUpvotes)
        db.session.commit()
        # flash("Your Answerupvotes has been registered.","success")
        print(answer_present)

        # Count all entries on that post
        upvoteCount = db.session.query(Answerupvotes).filter(Answerupvotes.answer_id == answer_id).count()
        answers.like_count = upvoteCount
        db.session.commit()

        print(db.session.query(Answerupvotes).filter(Answerupvotes.answer_id == answer_id).count())
        print(answers.like_count)
        print(answers)
        print("inside else")

        upvote = db.session.query(Answerupvotes).filter(Answerupvotes.answer_id == answer_id).count()
        downvote = db.session.query(Answerdownvotes).filter(Answerdownvotes.answer_id == answer_id).count()

        vote_data = {'vote_count': upvote, 'downvote_count': downvote}
        print('vote_data', vote_data)
        return jsonify(vote_data)

# ---------- Answer Downvotes route ---------
@app.route('/AnswerDownvotes/<int:answer_id>/<int:user_id>')
@login_required
def answerDislikes(answer_id,user_id):
    answers = Answer.query.get_or_404(answer_id)
    print(answers)

    # Check if entry is already present in the table
    answer_present = db.session.query(db.exists().where(and_(Answerdownvotes.answer_id == answer_id, Answerdownvotes.user_id == user_id))).scalar()
    # Check if user has Liked this post or not
    post_inAnswerUpvote = db.session.query(db.exists().where(and_(Answerupvotes.answer_id == answer_id, Answerupvotes.user_id == user_id))).scalar()


    if answer_present == True:
        print("All ready Downvoted")
        print(answer_id)
        print(user_id)
        print(answer_present)

        # If Yes, Delete the entry
        Answerdownvotes.query.filter_by(answer_id=answer_id, user_id=user_id).delete()
        Answerdownvotes.action = "not-liked"
        db.session.commit()
        # flash("Your vote has been removed.","success")

        # Count all entries on that post
        DownvoteCount = db.session.query(Answerdownvotes).filter(Answerdownvotes.answer_id == answer_id).count()
        answers.dislike_count = DownvoteCount
        db.session.commit()
        print(db.session.query(Answerdownvotes).filter(Answerdownvotes.answer_id == answer_id).count())
        print(answers.dislike_count)
        print(answers)
        print("inside if")
        
        upvote = db.session.query(Answerupvotes).filter(Answerupvotes.answer_id == answer_id).count()
        downvote = db.session.query(Answerdownvotes).filter(Answerdownvotes.answer_id == answer_id).count()

        vote_data = {'vote_count': upvote, 'downvote_count': downvote}
        print('vote_data', vote_data)
        return jsonify(vote_data)

        # If entry is not already present in the table
    elif post_inAnswerUpvote == True:
        Answerupvotes.query.filter_by(answer_id=answer_id, user_id=user_id).delete()
        print("Like Removed")
        db.session.commit()

        # Then add entry in the Downvote table
        answersDownvote = Answerdownvotes(user_id=user_id, answer_id=answer_id)
        answersDownvote.action = "not-liked"
        db.session.add(answersDownvote)
        db.session.commit()
        # flash("Your vote has been registered.","success")
        print(post_inAnswerUpvote)

        # Count all entries on that post
        upvoteCount = db.session.query(Answerupvotes).filter(Answerupvotes.answer_id == answer_id).count()
        answers.like_count = upvoteCount
        db.session.commit()

        DownvoteCount = db.session.query(Answerdownvotes).filter(Answerdownvotes.answer_id == answer_id).count()
        answers.dislike_count = DownvoteCount
        db.session.commit()

        print(db.session.query(Answerdownvotes).filter(Answerdownvotes.answer_id == answer_id).count())
        print(answers.dislike_count)
        print(answers)
        print("inside elif")

        upvote = db.session.query(Answerupvotes).filter(Answerupvotes.answer_id == answer_id).count()
        downvote = db.session.query(Answerdownvotes).filter(Answerdownvotes.answer_id == answer_id).count()

        vote_data = {'vote_count': upvote, 'downvote_count': downvote}
        print('vote_data', vote_data)
        return jsonify(vote_data)
    else:
        # Then add entry in the table
        answerDownvotes = Answerdownvotes(user_id=user_id, answer_id=answer_id)
        answerDownvotes .action = "not-liked"
        db.session.add(answerDownvotes )
        db.session.commit()
        # flash("Your Answerdownvotes has been registered.","success")
        print(answer_present)

        # Count all entries on that post
        downvoteCount = db.session.query(Answerdownvotes).filter(Answerdownvotes.answer_id == answer_id).count()
        answers.dislike_count = downvoteCount
        db.session.commit()

        print(db.session.query(Answerdownvotes).filter(Answerdownvotes.answer_id == answer_id).count())
        print(answers.dislike_count)
        print(answers)
        print("inside else")

        upvote = db.session.query(Answerupvotes).filter(Answerupvotes.answer_id == answer_id).count()
        downvote = db.session.query(Answerdownvotes).filter(Answerdownvotes.answer_id == answer_id).count()

        vote_data = {'vote_count': upvote, 'downvote_count': downvote}
        print('vote_data', vote_data)
        return jsonify(vote_data)

# ---------- Answer Update  route ---------
@app.route("/answer/<int:post_id>/<int:answer_id>/update", methods=['GET', 'POST'])
@login_required
def update_answer(answer_id, post_id):
    answer = Answer.query.get_or_404(answer_id)
    print(answer)
    post = Post.query.get_or_404(post_id)
    # Join tables (tagposts, Tags and Post) to get tags for each post
    joinedTables = db.session.query(tagposts.post_id,tagposts.tag_id,Tags.tag_title,Post.title,Post.user_id,Post.like_count,Post.content).join(Tags).join(Post).all()




    # If answer author is not current user then abort
    if answer.author != current_user:
        abort(403)
    # Else if current user is author then import the form
    if request.method == 'POST':
        answer.content = request.form.get('editordata')
        db.session.commit()
        return redirect(url_for('comment_post', post_id=post_id))


    # Populate form with current answer data
    elif request.method == 'GET':

        return render_template('editAnswer.html',post=post, answer=answer, joinedTables=joinedTables, title='Update Answer', legend='Edit Your Answer')

# ---------- Favourite Posts routes ----------
@app.route("/favourite/<int:post_id>", methods=['GET', 'POST'])
def favourite_post(post_id):
    post = Post.query.get_or_404(post_id)

    post_present = db.session.query(db.exists().where(and_(Favourite.post_id == post_id, Favourite.current_user_id == current_user.id))).scalar()

    if post_present == True:
        flash("Post is already in favourites", 'success')
    else:
        addFavourite = Favourite(post_id=post_id, user_id=post.user_id, current_user_id=current_user.id, title=post.title,content=post.content,date_posted=post.date_posted,like_count=post.like_count, dislike_count=post.dislike_count)
        db.session.add(addFavourite)
        db.session.commit()
        flash("Post has been added to favourites", 'success')

    return redirect(url_for('home'))

# ---------- Show Favourite Posts routes ----------
@app.route("/favourite", methods=['GET', 'POST'])
def favourite():

    page = request.args.get('page',1,type=int)
    posts = Favourite.query.filter_by(current_user_id=current_user.id).order_by(Favourite.id.desc()).paginate(page=page, per_page=5)

    # Join tables (tagposts, Tags and Post) to get tags for each post
    joinedTables = db.session.query(tagposts.post_id,tagposts.tag_id,Tags.tag_title,Post.title,Post.user_id,Post.like_count,Post.content,Post.id,Post.author,Post.date_posted,User.username,User.image_file, Favourite.post_id, Favourite.user_id).join(Tags).join(Post).join(User).join(Favourite).all()
    # print(joinedTables)




    return render_template("favourite.html", posts=posts, joinedTables=joinedTables)

# ---------- Delete Favourite Posts routes ----------
@app.route("/delete/favourites/<int:post_id>", methods=['GET', 'POST'])
def delete_favourites(post_id):
    Favourite.query.filter_by(post_id=post_id).delete()
    db.session.commit()
    return redirect(url_for('favourite'))