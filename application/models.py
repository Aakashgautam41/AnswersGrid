from datetime import datetime
from application import db, login_manager, app
from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)
    answers = db.relationship('Answer', backref="author", lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
    answercomments = db.relationship('AnswerComment', backref='author', lazy=True)
    favourites = db.relationship('Favourite', backref='author', lazy=True)

    # Method to create token
    def get_reset_token(self, expires_sec=1800):
        s = Serializer(app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    # Method to verify token
    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    like_count = db.Column(db.Integer, nullable=False, default=0)
    dislike_count = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='commentOnPost', lazy=True)
    answers = db.relationship('Answer', backref='answerOnPost', lazy=True)
    favourites = db.relationship('Favourite', backref='favour_post', lazy=True)

    def __repr__(self):
        return f"('{self.id}','{self.title}', '{self.date_posted}', '{self.like_count}','{self.dislike_count}')"

class Comment(db.Model):
    comment_id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    answer_id = db.Column(db.Integer, db.ForeignKey('answer.id'), nullable=False)

    def __repr__(self):
        return f"Comment('{self.comment}', '{self.date_posted}')"

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer,nullable=False)
    post_id = db.Column(db.Integer,nullable=False)
    action = db.Column(db.String,nullable=False)

    def __repr__(self):
        return f"Vote('{self.user_id}', '{self.post_id}', '{self.action}')"

class Downvote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer,nullable=False)
    post_id = db.Column(db.Integer,nullable=False)
    action = db.Column(db.String,nullable=False)

    def __repr__(self):
        return f"Downvote('{self.user_id}', '{self.post_id}', '{self.action}')"


class Tags(db.Model):
    tag_id = db.Column(db.Integer, primary_key=True, nullable=False)
    tag_title = db.Column(db.String,nullable=False)
    # tag_id = db.relationship('Tags'), backref='tagId', lazy=True)

    def __repr__(self):
        return f"Tags('{self.tag_id}', '{self.tag_title}')"


class tagposts(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.tag_id'), nullable=False)

    def __repr__(self):
        return f"tagposts('{self.post_id}', '{self.tag_id}')"


# Answers Models
class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    like_count = db.Column(db.Integer, nullable=False, default=0)
    dislike_count = db.Column(db.Integer, nullable=False, default=0)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='commentsOnPost', lazy=True)
    answercomments = db.relationship('AnswerComment', backref='commentsOnAnswer', lazy=True)

    def __repr__(self):
        return f"Answer('{self.content}',{self.date_posted}', '{self.like_count}','{self.post_id}', '{self.user_id}')"

class AnswerComment(db.Model):
    comment_id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    answer_id = db.Column(db.Integer, db.ForeignKey('answer.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
  

    def __repr__(self):
        return f"AnswerComment('{self.comment}', '{self.date_posted}')"
class Answerupvotes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer,nullable=False)
    answer_id = db.Column(db.Integer,nullable=False)
    action = db.Column(db.String,nullable=False)

    def __repr__(self):
        return f"Answerupvotes('{self.user_id}', '{self.answer_id}', '{self.action}')"

class Answerdownvotes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer,nullable=False)
    answer_id = db.Column(db.Integer,nullable=False)
    action = db.Column(db.String,nullable=False)

    def __repr__(self):
        return f"Answerdownvotes('{self.user_id}', '{self.answer_id}', '{self.action}')"

        
class Favourite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    current_user_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    like_count = db.Column(db.Integer, nullable=False, default=0)
    dislike_count = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f"Favourite('{self.user_id}', '{self.post_id}', '{self.title}', '{self.date_posted}', '{self.like_count}')"