from flask import render_template, url_for, flash, redirect, request, abort, jsonify
from application import app, db, bcrypt
from application.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm, CommentForm, SearchForm
from application.models import User, Post, Comment, Vote, Downvote, Tags, tagposts
from flask_login import login_user, current_user, logout_user, login_required
import secrets
import os
from PIL import Image
from sqlalchemy.sql import exists
from sqlalchemy import func
from sqlalchemy import and_
from sqlalchemy import create_engine


@app.route("/")
@app.route("/home")
def home():
    page = request.args.get('page',1,type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    voted = Vote.query.order_by(Vote.post_id.desc())

    # Join tables (tagposts, Tags and Post) to get tags for each post
    joinedTables = db.session.query(tagposts.post_id,tagposts.tag_id,Tags.tag_title,Post.title,Post.user_id,Post.like_count,Post.content).join(Tags).join(Post).all()
    # print(joinedTables)

    return render_template('home.html', posts=posts, voted=voted, joinedTables=joinedTables)


@app.route("/about")
def about():
    return render_template('about.html', title='About')

@app.route("/getdata")
def getdata():
    posts = ['a','b','c']
    # tags = [('73', 'Flask'),('70', 'Jquery'),('69', 'Python'),('72', 'Python'),('71', 'SQLAlchemy')]
    x = Tags.query.order_by(Tags.tag_title).all()

    z=[]
    
    for y in x:
        z.append(str(y.tag_title))
    print(z)
     

    return jsonify(z)

    # return jsonify({'data' :render_template("data.html", posts=posts)})


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
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            flash('You have been logged in!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
            return redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

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


@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()

        tag = Tags(tag_title=form.tags.data)
        db.session.add(tag)
        db.session.commit()

        post = Post.query.order_by(Post.date_posted.desc()).first()
        post_id = post.id

        tag = Tags.query.order_by(Tags.tag_id.desc()).first()
        tag_id = tag.tag_id
        print(post_id)
        print(tag_id)

        something = tagposts(post_id=post_id, tag_id=tag_id)
        db.session.add(something)
        db.session.commit()
        flash('Your question has been posted', 'success')


    return render_template('create_post.html', title='Ask Question', form=form, legend='Ask Question')


@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html',title=post.title,post=post)


@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    tagpost = tagposts.query.filter_by(post_id=post_id).first_or_404()
    tagId = tagpost.tag_id
    tag = Tags.query.filter_by(tag_id=tagId).first_or_404()
    
    # If post author is not current user then abort
    if post.author != current_user:
        abort(403)
    # Else if current user is author then import the form
    form = PostForm()
    # Update post if form is valid
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        tag.tag_title = form.tags.data
        db.session.commit()
        flash('Your question has been updated', 'success')
        return redirect(url_for('post', post_id=post_id))
    # Populate form with current post data
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
        form.tags.data = tag.tag_title
        return render_template('create_post.html', title='Update Post',form=form, legend='Edit Your Question')


@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your question has been deleted', 'success')
    return redirect(url_for('home'))


@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user)\
        .order_by(Post.date_posted.desc())\
        .paginate(page=page, per_page=5)
    return render_template('user_posts.html', posts=posts, user=user)


@app.route("/post/<int:post_id>/comment", methods=['GET', 'POST'])
@login_required
def comment_post(post_id):
    post = Post.query.get_or_404(post_id)
    posts_id = post.id

    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(comment=form.comment.data, post_id=posts_id, user_id=current_user.id)
        post = Post.query.get_or_404(post_id)
        db.session.add(comment)
        db.session.commit()
        print(current_user.id)
        comments = Comment.query.filter(Comment.post_id == post_id).order_by(Comment.date_posted.desc())
        flash('Your comment has been posted', 'success')
        return render_template('comment_post.html', title='Comment', form=form, post=post, comments=comments)
    else:
        comments = Comment.query.filter(Comment.post_id == post_id).order_by(Comment.date_posted.desc())
        return render_template('comment_post.html', title='Comment', form=form, post=post, comments=comments)


@app.route("/search", methods=['GET', 'POST'])
def search():
        page = request.args.get('page', 1, type=int)
        searched_content = request.form.get('search')
        searched_posts = Post.query.filter(Post.content.like('%'+searched_content+'%')).paginate(page=page, per_page=5)
        return render_template('search.html', searched_posts=searched_posts)


@app.route('/vote/<int:post_id>/<int:user_id>')
@login_required
def upvote(post_id,user_id):
    posts = Post.query.get_or_404(post_id)

    # Check if entry is already present in the table
    post_present = db.session.query(db.exists().where(and_(Vote.post_id == post_id, Vote.user_id == user_id))).scalar()

    if post_present == True:
        print("All ready upvoted")
        print(post_id)
        print(user_id)
        print(post_present)

        # If YES, Delete the entry
        Vote.query.filter_by(post_id=post_id, user_id=user_id).delete()
        Vote.action = "not-liked"
        db.session.commit()
        flash("Your vote has been removed.","success")

        # Count all entries on that post
        upvoteCount = db.session.query(Vote).filter(Vote.post_id == post_id).count()
        posts.like_count = upvoteCount
        db.session.commit()
        print(db.session.query(Vote).filter(Vote.post_id == post_id).count())
        print(posts.like_count)
        print(posts)

    # If entry is not already present in the table
    else:
        # Then add entry in the table
        vote = Vote(user_id=user_id, post_id=post_id)
        vote.action = "liked"
        db.session.add(vote)
        db.session.commit()
        flash("Your vote has been registered.","success")
        print(post_present)

        # Count all entries on that post
        upvoteCount = db.session.query(Vote).filter(Vote.post_id == post_id).count()
        posts.like_count = upvoteCount
        db.session.commit()
        print(db.session.query(Vote).filter(Vote.post_id == post_id).count())
        print(posts.like_count)
        print(posts)

    return redirect("/home")

@app.route('/downvote/<int:post_id>/<int:user_id>')
@login_required
def downvote(post_id,user_id):
    posts = Post.query.get_or_404(post_id)

    # Check if entry is already present in the table
    post_present = db.session.query(db.exists().where(and_(Downvote.post_id == post_id, Downvote.user_id == user_id))).scalar()

    if post_present == True:
        print("All ready downvoted")
        print(post_id)
        print(user_id)
        print(post_present)

        # If YES, Delete the entry
        Downvote.query.filter_by(post_id=post_id, user_id=user_id).delete()
        db.session.commit()
        flash("Your downvote has been removed !!","success")

        # Count all entries on that post
        DownvoteCount = db.session.query(Downvote).filter(Downvote.post_id == post_id).count()
        posts.dislike_count = DownvoteCount
        db.session.commit()
        print(db.session.query(Downvote).filter(Downvote.post_id == post_id).count())
        print(posts.dislike_count)
        print(posts)

    # If entry is not already present in the table
    else:
        # Then add entry in the table
        downvote = Downvote(user_id=user_id, post_id=post_id)
        downvote.action = "disliked"
        db.session.add(downvote)
        db.session.commit()
        flash("You have disliked the post","success")
        print(post_present)

        # Count all entries on that post
        downvoteCount = db.session.query(Downvote).filter(Downvote.post_id == post_id).count()
        posts.dislike_count = downvoteCount
        db.session.commit()
        print(db.session.query(Downvote).filter(Downvote.post_id == post_id).count())
        print(posts.dislike_count)
        print(posts)

    return redirect("/home")



@app.route('/tags/<tag_title>')
def tags(tag_title):
    page = request.args.get('page',1,type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    tag_title = tag_title

    # Join tables (tagposts, Tags and Post) to get tags for each post
    joinedTables = db.session.query(tagposts.post_id,tagposts.tag_id,Tags.tag_title,Post.title,Post.user_id,Post.like_count,Post.content,Post.id,Post.author,Post.date_posted,User.username,User.image_file).join(Tags).join(Post).join(User).all()
    # print(joinedTables)

    for item in joinedTables:
        if tag_title in item.tag_title:
            print(tag_title, item.post_id, item.title, item.user_id,  item.username, item.image_file)


            return render_template("tags.html", posts=posts, joinedTables=joinedTables, tag_title=tag_title)



# TODO
# Check if entry is already present in the table -- Done
# If YES then delete the entry          --Done
# Then count all entries on that post   -- Done

# If entry is not already present in the table   --Done
# Then add entry in the table   --Done
# Count all entries on that post   --Done


# TODO
# Update upvote/downvote without refeshing page

# TODO
# Show tags on posts  -- Done

# TODO
# Make different route for tags
# Make tags.html  --Done
# When user clicks tag on post it should show all posts containing same tags  -- Done