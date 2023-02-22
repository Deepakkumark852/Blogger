from flask import Flask,request,g,render_template,flash,redirect,url_for,session,logging
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import MetaData
from datetime import datetime
from sqlalchemy.engine import Engine
from sqlalchemy import event

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()



app = Flask(__name__)
app.secret_key = 'secret123'
session_type = 'sqlalchemy'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']: 'False'
db = SQLAlchemy(app)
migrate = Migrate(app,db,render_as_batch=True)
app.app_context().push()


# create the database model
class user(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), unique=True, nullable=False)
    name= db.Column(db.String(80))
    posts = db.relationship('Blog', backref='author', lazy=True, passive_deletes=True)
    followers = db.relationship('follow', backref='follower', lazy=True, passive_deletes=True, foreign_keys='follow.follower_id')
    followed = db.relationship('follow', backref='followed', lazy=True, passive_deletes=True , foreign_keys='follow.followed_id')
    feeds = db.relationship('feed', backref='user', lazy=True, passive_deletes=True)
    img = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return '<User %r>' % self.name
    
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Blog(db.Model):
    __tablename__ = 'Blog'
    id = db.Column(db.Integer, primary_key=True , autoincrement=True)
    title = db.Column(db.String(150), unique=True, nullable=False)
    content = db.Column(db.String(100000), unique=True, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete = "CASCADE"), nullable=False)
    date = db.Column(db.String(80) ,nullable=False)
    feeds = db.relationship('feed', backref='blog', lazy=True, passive_deletes=True)
    img = db.Column(db.Text, nullable=True)


    def __repr__(self):
        return '<Blog %r>' % self.title
    
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class follow(db.Model):
    __tablename__ = 'follow'
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete = "CASCADE", onupdate = "CASCADE"), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id',ondelete = "CASCADE", onupdate = "CASCADE"), nullable=False)
    follow_date = db.Column(db.String(80), nullable=False)
    mutual = db.Column(db.String(80))
    followed_name = db.Column(db.String(80), nullable=False)
    follower_name = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return '<follow %r>' % self.id
    
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class feed(db.Model):
    __tablename__ = 'feed'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id',ondelete = "CASCADE",onupdate = "CASCADE" ), nullable=False)
    blog_id = db.Column(db.Integer, db.ForeignKey('Blog.id',ondelete = "CASCADE", onupdate = "CASCADE"), nullable=False)
    date = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return '<feed %r>' % self.id

# create and configure the app
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['submit'] == 'Log In':
            name = request.form['username']
            password = request.form['password']
            users = user.query.filter_by(username=name).first()
            if users is not None:
                if users.password == password:
                    session['logged_in'] = True
                    session['username'] = name
                    session['name'] = users.name
                    session['id'] = users.id
                    return redirect(url_for('dashboard'))
                else:
                    flash('Wrong password', 'danger')
                    print("DDd")
                    return render_template('login.html')
            else:
                flash('User not found', 'danger')
                return render_template('login.html')
        else:
            return redirect(url_for('register'))
    else:
        if 'logged_in' in session:
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    else:
        if request.method == 'POST':
            name = request.form['name']
            username = request.form['username']
            password = request.form['password']
            img = request.files['image']
            users = user.query.filter_by(username=username).first()
            if users is not None:
                flash('User already exists', 'danger')
                return render_template('register.html')
            else:
                user1 = user(username=username, password=password, name=name, img=img.read())
                db.session.add(user1)
                db.session.commit()
                flash('User created', 'success')
                return redirect(url_for('login'))
        else:
            return render_template('register.html')


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'logged_in' in session:
        posts = []
        feeds = feed.query.all()
        for post in feeds:
            if post.user_id == user.query.filter_by(username=session['username']).first().id:
                post=Blog.query.filter_by(id=post.blog_id).first()
                users = user.query.filter_by(id=post.author_id).first()
                print( "post " ,(post,users.username,users.name))
                posts.append((post,users.username,users.name))
        return render_template('dashboard.html', posts=posts , name = session['username'])
    else:
        return redirect(url_for('login'))


@app.route('/profile/<string:id>')
def profile(id):
    if 'logged_in' in session:
        followed_users=[]
        followers_users=[]

        users = user.query.filter_by(username = id ).first()
        user1 = users.as_dict()
        posts =[row.as_dict() for row in Blog.query.filter(Blog.author_id == users.id).all()]
        #print("posts",posts)

        for post in posts:
            fp = open("static/img/"+str(post['id'])+".png", "wb")
            fp.write(post['img'])
            fp.close()

        followed = follow.query.filter(follow.follower_id == users.id).all()
        followers = follow.query.filter(follow.followed_id == users.id).all()
        

        #print("followers",followers)
        #print("followed",followed)

        for follows in followed:
            print("follow",follows)
            followed_users.append(user.query.filter_by(id=follows.followed_id).first().username)
        for follows in followers:
            followers_users.append(user.query.filter_by(id=follows.follower_id).first().username)

        followed =[row.as_dict() for row in follow.query.filter(follow.follower_id == users.id).all()]
        followers =[row.as_dict() for row in follow.query.filter(follow.followed_id == users.id).all()]

        count_followers = len(followers)
        count_followed = len(followed)
        count_posts = len(posts)
        fp=open('static/img/profile.png','wb+')
        fp.write(users.img)
        fp.close()
        context = {
            'user1': user1,
            'posts': posts,
            'followed': followed,
            'followers': followers,
            'count_followers': count_followers,
            'count_followed': count_followed,
            'count_posts': count_posts,
            'followed_users': followed_users,
            'follower_users': followers_users

        }
        cont={
            'posts': posts,
        }
        context['user'] = users
        print(session.keys())
        return render_template('profile.html', context=context, name = session['username'], id=session['id'])
    else:
        return redirect(url_for('login'))


@app.route('/editprofile', methods=['GET', 'POST'])
def editprofile():
    if 'logged_in' in session:
        if request.method == 'POST':
            name = request.form['name']
            username = request.form['username']
            users = user.query.filter_by(username=session['username']).first()
            users.name = name
            users.username = username
            follow.query.filter_by(follower_id=users.id).update({"follower_name": name})
            follow.query.filter_by(followed_id=users.id).update({"followed_name": name})
            db.session.commit()
            flash('Profile updated', 'success')
            return redirect(url_for('editprofile'))
        else:
            users = user.query.filter_by(username=session['username']).first()
            return render_template('editprofile.html', user=users)
    else:
        return redirect(url_for('login'))



@app.route('/deleteaccount', methods=['GET', 'POST'])
def deleteaccount():
    if 'logged_in' in session:
            users = user.query.filter_by(username=session['username']).first()
            #db.session.delete(users.posts)
            db.session.delete(users)
            db.session.commit()
            flash('Profile deleted', 'success')
            session.clear()
            return redirect(url_for('login'))
    else:
        return redirect(url_for('login'))



@app.route('/new_post', methods=['GET', 'POST'])
def new_post():
    if 'logged_in' in session:
        if request.method == "POST":
            title = request.form['title']
            content = request.form['content']
            img = request.files['image']
            date = datetime.now()
            author_id = user.query.filter_by(username=session['username']).first().id
            b = Blog(title=title, content=content, date=date, author_id=author_id, img=img.read())
            db.session.add(b)
            db.session.commit()
            followings = follow.query.filter_by(followed_id=author_id).all()
            for following in followings:
                date = datetime.now()
                f = feed(user_id=following.follower_id, blog_id=b.id, date=date)
                db.session.add(f)
                db.session.commit()
            flash('Post created', 'success')
            return redirect(url_for('dashboard'))
        else:
            return render_template('addpost.html', name = session['username'])
    else:
        return redirect(url_for('login'))

@app.route("/editpost", methods = ['GET', 'POST'])
def editpost():
    if 'logged_in' in session:
        if request.method == "POST":
            id= request.args.get('submit')
            posts =[row.as_dict() for row in Blog.query.filter(Blog.author_id == session['id']).all()]
            id = posts[int(id)]['id']
            b = Blog.query.filter_by(id = id).first()
            b.title = request.form['title']
            b.content = request.form['content']
            b.date = datetime.now()
            db.session.commit()
            flash('Post updated', 'success')
            return redirect(url_for('dashboard'))
        else:
            id = request.args.get('submit')
            posts =[row.as_dict() for row in Blog.query.filter(Blog.author_id == session['id']).all()]
            b = posts[int(id)]['id']
            b=Blog.query.filter_by(id=b).first()
            fp=open('static/img/post.png','wb+')
            fp.write(b.img)
            fp.close()
            #print(b)
            return render_template('editpost.html', name = session['username'], post=b)
    else:
        return redirect(url_for('login'))

@app.route("/deletepost", methods = ['GET', 'POST'])
def deletepost():
    if 'logged_in' in session:
        id = request.args.get('delete')
        posts =[row.as_dict() for row in Blog.query.filter(Blog.author_id == session['id']).all()]
        b= posts[int(id)]['id']
        b=Blog.query.filter_by(id=b).first()
        db.session.delete(b)
        db.session.commit()
        flash('Post deleted', 'success')
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/search', methods=['GET', 'POST'])
def search():
    if 'logged_in' in session:

        search = None
        followed_users=[]
        followers_users=[]

        if request.method == "POST":
            search = request.form['search']

        #print("sessionkeys",session.keys())  

        if search or ('search' in session.keys()):
            
            if not search:
                search = session['search']
                if not request.args.get('page'):
                    del session['search']
            else:
                session['search'] = search

            lst=[i[0] for i in follow.query.with_entities(follow.followed_id).filter_by(follower_id = session['id']).all() ]
            lst = lst +[i[0] for i in follow.query.with_entities(follow.follower_id).filter_by(followed_id = session['id']).all()]
            #print("lst",lst)


            users = [row.as_dict() for row in user.query.filter(user.id.notin_(lst)).filter(user.id != session['id']).filter(user.name.startswith(search)).all()]
            followed = follow.query.filter_by(follower_id = session['id']).filter(follow.followed_name.startswith(search)).all()
            followers = follow.query.filter_by(followed_id = session['id']).filter(follow.follower_name.startswith(search)).filter(follow.mutual != 1).all()

            #print("users",users)
            #print("followed",followed)
            #print("followers",followers)


            for follows in followed:
                followed_users.append(user.query.filter_by(id=follows.followed_id).first().as_dict())
            for follows in followers:
                followers_users.append(user.query.filter_by(id=follows.follower_id).first().as_dict())

            '''print("user",users)
            print("followed",followed_users)
            print("followers",followers_users)'''

            context = {
                'users': users,
                'followed': followed_users,
                'followers': followers_users
            }


            return render_template('search.html', cont=context, name = session['username'])

        else:
            return render_template('search.html', name = session['username'], cont={})
    else:
        return redirect(url_for('login'))


@app.route('/createfollow/<string:id>', methods=['GET'])
def createfollow(id):
    if 'logged_in' in session:
            #print("create follow accessed"))
            followed_id = user.query.filter_by(id=id).first().id
            followed_name = user.query.filter_by(id=id).first().name
            follower_id = session['id']
            follower_name = session['name']
            followed_date  = datetime.now()
            f = follow(followed_id=followed_id, followed_name=followed_name, follower_id=follower_id, follower_name=follower_name, follow_date=followed_date)
            
            '''print("followed_id",followed_id)
            print("follower_id",follower_id)
            print("fff",f.followed_id)
            print("follower",f.follower_id)'''

            if follow.query.filter_by(follower_id = followed_id).filter_by(followed_id = follower_id).first():
                f.mutual = 1
                f1 = follow.query.filter_by(follower_id = followed_id).filter_by( followed_id = follower_id).first()
                f1.mutual =1

            db.session.add(f)
            db.session.commit()
            flash('Followed', 'success')
            return redirect(url_for('search'))
            #return redirect(url_for(f"profile"))
    else:
        return redirect(url_for('login'))


@app.route('/deletefollow/<string:id>', methods=['GET'])
def deletefollow(id):
    print("delete follow accessed")
    if 'logged_in' in session:
        f= follow.query.filter_by(followed_id = id).filter_by(follower_id = session['id']).first()
        if f.mutual == '1':
            f1= follow.query.filter_by(followed_id = session['id']).filter_by(follower_id = id).first()
            f1.mutual = 0
        db.session.delete(f)
        db.session.commit()
        flash('Unfollowed', 'success')
        return redirect(url_for('search',page ='1'))
    else:
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You are logged out', 'success')
    return redirect(url_for('login'))



if __name__ == '__main__':
    db.create_all()
    app.run(debug =True)

