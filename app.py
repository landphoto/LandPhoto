# -*- coding: utf-8 -*-
import os, json, secrets, re, datetime as dt
from pathlib import Path
from datetime import timedelta
from PIL import Image
import requests

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ======================= Paths & App =======================
BASE_DIR   = Path(__file__).parent.resolve()
INSTANCE   = BASE_DIR / "instance"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
THUMB_DIR  = BASE_DIR / "static" / "thumbs"
AVATAR_DIR = BASE_DIR / "static" / "avatars"
CHAT_UPLOAD_DIR = BASE_DIR / "static" / "chat_uploads"
CHAT_THUMB_DIR  = BASE_DIR / "static" / "chat_thumbs"
for p in (INSTANCE, UPLOAD_DIR, THUMB_DIR, AVATAR_DIR, CHAT_UPLOAD_DIR, CHAT_THUMB_DIR):
    p.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, instance_path=str(INSTANCE))
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", secrets.token_hex(16)),
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{INSTANCE/'landphoto.db'}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAX_CONTENT_LENGTH=25*1024*1024,
    JSON_AS_ASCII=False
)

# مفتاح GIPHY (اللي عطيتنياه)
GIPHY_API_KEY = os.environ.get("GIPHY_API_KEY", "z8wGcFNoHvLteHRN1AFAto0CcTXK1log")

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "auth_login"

# ======================= Consts =======================
ALLOWED_EXT   = {"png","jpg","jpeg","gif","webp"}
CHAT_ALLOWED  = {"png","jpg","jpeg","gif","webp"}
COMMENT_EMOJIS = ["❤️","🔥","😍","👏","😂","👌","✨","💯"]
USERNAME_RE    = re.compile(r"^[A-Za-z0-9_.]{3,32}$")

# ======================= Models =======================
class Follow(db.Model):
    __tablename__="follows"
    follower_id=db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    followed_id=db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    created_at=db.Column(db.DateTime, default=dt.datetime.utcnow)

class User(UserMixin, db.Model):
    __tablename__="users"
    id=db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(32), unique=True, nullable=False, index=True)
    email=db.Column(db.String(120), unique=True)
    password_hash=db.Column(db.String(255), nullable=False)
    display_name=db.Column(db.String(80))
    bio=db.Column(db.String(280))
    avatar_file=db.Column(db.String(255))
    notify_likes=db.Column(db.Boolean, default=True)
    notify_comments=db.Column(db.Boolean, default=True)
    notify_follows=db.Column(db.Boolean, default=True)
    last_seen=db.Column(db.DateTime, default=dt.datetime.utcnow, index=True)

    photos=db.relationship("Photo", backref="author", lazy="dynamic")
    given_likes=db.relationship("Like", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    bookmarks=db.relationship("Bookmark", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    comments=db.relationship("Comment", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    following=db.relationship(
        "User", secondary="follows",
        primaryjoin=id==Follow.follower_id,
        secondaryjoin=id==Follow.followed_id,
        backref=db.backref("followers", lazy="dynamic"),
        lazy="dynamic"
    )

    def set_password(self,pw): self.password_hash=generate_password_hash(pw)
    def check_password(self,pw): return check_password_hash(self.password_hash, pw)

    @property
    def avatar_url(self):
        if self.avatar_file and (AVATAR_DIR/self.avatar_file).exists():
            return url_for("static", filename=f"avatars/{self.avatar_file}")
        return url_for("static", filename="avatars/default.png")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name or self.username,
            "avatar": self.avatar_url
        }

class Photo(db.Model):
    __tablename__="photos"
    id=db.Column(db.Integer, primary_key=True)
    user_id=db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    caption=db.Column(db.Text)
    tags=db.Column(db.String(240))
    allow_comments=db.Column(db.Boolean, default=True)
    allow_share=db.Column(db.Boolean, default=True)
    created_at=db.Column(db.DateTime, default=dt.datetime.utcnow, index=True)

    images=db.relationship("PhotoImage", backref="photo", cascade="all, delete-orphan")
    likes=db.relationship("Like", backref="photo", cascade="all, delete-orphan")
    comments=db.relationship("Comment", backref="photo", cascade="all, delete-orphan")
    bookmarks=db.relationship("Bookmark", backref="photo", cascade="all, delete-orphan")

    @property
    def like_count(self): return len(self.likes)
    @property
    def comment_count(self): return len(self.comments)
    @property
    def image_count(self): return len(self.images)

    def is_liked_by(self, user):
        return user.is_authenticated and Like.query.filter_by(user_id=user.id, photo_id=self.id).first() is not None

    def is_bookmarked_by(self, user):
        return user.is_authenticated and Bookmark.query.filter_by(user_id=user.id, photo_id=self.id).first() is not None

class PhotoImage(db.Model):
    __tablename__="photo_images"
    id=db.Column(db.Integer, primary_key=True)
    photo_id=db.Column(db.Integer, db.ForeignKey("photos.id"), nullable=False)
    filename=db.Column(db.String(255), nullable=False)
    thumbfile=db.Column(db.String(255), nullable=False)
    @property
    def url(self): return url_for("static", filename=f"uploads/{self.filename}")
    @property
    def thumb_url(self): return url_for("static", filename=f"thumbs/{self.thumbfile}")

class Like(db.Model):
    __tablename__="likes"
    id=db.Column(db.Integer, primary_key=True)
    user_id=db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    photo_id=db.Column(db.Integer, db.ForeignKey("photos.id"), nullable=False)
    created_at=db.Column(db.DateTime, default=dt.datetime.utcnow)
    __table_args__=(db.UniqueConstraint("user_id","photo_id", name="uix_like_once"),)

class Bookmark(db.Model):
    __tablename__="bookmarks"
    id=db.Column(db.Integer, primary_key=True)
    user_id=db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    photo_id=db.Column(db.Integer, db.ForeignKey("photos.id"), nullable=False)
    created_at=db.Column(db.DateTime, default=dt.datetime.utcnow)
    __table_args__=(db.UniqueConstraint("user_id","photo_id", name="uix_bookmark_once"),)

class Comment(db.Model):
    __tablename__="comments"
    id=db.Column(db.Integer, primary_key=True)
    photo_id=db.Column(db.Integer, db.ForeignKey("photos.id"), nullable=False)
    user_id=db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content=db.Column(db.String(600))
    created_at=db.Column(db.DateTime, default=dt.datetime.utcnow)
    reactions=db.relationship("CommentReaction", backref="comment", cascade="all, delete-orphan")
    def reaction_count(self, emoji): return CommentReaction.query.filter_by(comment_id=self.id, emoji=emoji).count()
    def reacted(self, user, emoji):
        return user.is_authenticated and CommentReaction.query.filter_by(comment_id=self.id, user_id=user.id, emoji=emoji).first() is not None

class CommentReaction(db.Model):
    __tablename__="comment_reactions"
    id=db.Column(db.Integer, primary_key=True)
    comment_id=db.Column(db.Integer, db.ForeignKey("comments.id"), nullable=False)
    user_id=db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    emoji=db.Column(db.String(8), nullable=False)
    created_at=db.Column(db.DateTime, default=dt.datetime.utcnow)
    __table_args__=(db.UniqueConstraint("comment_id","user_id","emoji", name="uix_comment_react_once"),)

# ---------- Chat ----------
class ChatThread(db.Model):
    __tablename__="chat_threads"
    id=db.Column(db.Integer, primary_key=True)
    user1_id=db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user2_id=db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    updated_at=db.Column(db.DateTime, default=dt.datetime.utcnow, index=True)

class ChatMessage(db.Model):
    __tablename__="chat_messages"
    id=db.Column(db.Integer, primary_key=True)
    thread_id=db.Column(db.Integer, db.ForeignKey("chat_threads.id"), nullable=False, index=True)
    sender_id=db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body=db.Column(db.String(1000), nullable=True)
    created_at=db.Column(db.DateTime, default=dt.datetime.utcnow, index=True)
    read_at=db.Column(db.DateTime, nullable=True, index=True)
    # attachments
    attachment_file  = db.Column(db.String(255), nullable=True)
    attachment_thumb = db.Column(db.String(255), nullable=True)
    attachment_type  = db.Column(db.String(20),  nullable=True)  # "image" | "gif"

# ======================= Helpers =======================
@login_manager.user_loader
def load_user(uid): return User.query.get(int(uid))

def sorted_pair(a,b): return (a,b) if a<b else (b,a)
def is_following(u_from_id,u_to_id):
    return Follow.query.filter_by(follower_id=u_from_id, followed_id=u_to_id).first() is not None
def can_message(me, other): return is_following(me.id, other.id)

def is_online(user):
    if not user or not getattr(user, "last_seen", None): return False
    return (dt.datetime.utcnow() - user.last_seen) < timedelta(minutes=3)

@app.before_request
def update_last_seen():
    if current_user.is_authenticated:
        current_user.last_seen = dt.datetime.utcnow()
        db.session.commit()

def allowed_file(fn): return "." in fn and fn.rsplit(".",1)[1].lower() in ALLOWED_EXT

def make_filename(prefix, original):
    ext=original.rsplit(".",1)[-1].lower()
    token=f"{int(dt.datetime.utcnow().timestamp())}_{secrets.token_hex(4)}"
    return secure_filename(f"{prefix}_{token}.{ext}")

def save_image(file_storage, prefix="IMG"):
    filename=make_filename(prefix, file_storage.filename)
    full_path=UPLOAD_DIR/filename
    file_storage.save(full_path)
    thumbname=filename.rsplit(".",1)[0]+"_th.jpg"
    with Image.open(full_path) as im:
        im=im.convert("RGB")
        w,h=im.size; s=min(w,h); l=(w-s)//2; t=(h-s)//2
        im=im.crop((l,t,l+s,t+s)).resize((680,680), Image.LANCZOS)
        im.save(THUMB_DIR/thumbname, "JPEG", quality=88, optimize=True)
    return filename, thumbname

# --- chat attachments ---
def chat_file_url(name):  return url_for("static", filename=f"chat_uploads/{name}")
def chat_thumb_url(name): return url_for("static", filename=f"chat_thumbs/{name}")

def save_chat_image(file_storage):
    if not file_storage or not file_storage.filename: return None
    ext = file_storage.filename.rsplit(".",1)[-1].lower()
    if ext not in CHAT_ALLOWED: return None

    token = f"{int(dt.datetime.utcnow().timestamp())}_{secrets.token_hex(4)}"
    fname = secure_filename(f"CHAT_{token}.{ext}")
    fpath = CHAT_UPLOAD_DIR / fname
    file_storage.save(fpath)

    # GIF: فقط مصغّر JPG
    if ext == "gif" or ext == "webp":
        try:
            with Image.open(fpath) as im:
                im = im.convert("RGB")
                im.thumbnail((420,420), Image.LANCZOS)
                tname = fname.rsplit(".",1)[0] + "_th.jpg"
                im.save(CHAT_THUMB_DIR/tname, "JPEG", quality=85, optimize=True)
        except Exception:
            tname = None
        return fname, tname, "gif"

    # باقي الصور: تحويل لمربع + مصغّر
    with Image.open(fpath) as im:
        im = im.convert("RGB")
        w,h=im.size; s=min(w,h); l=(w-s)//2; t=(h-s)//2
        im_crop = im.crop((l,t,l+s,t+s)).resize((900,900), Image.LANCZOS)
        im_crop.save(fpath, "JPEG", quality=88, optimize=True)
        tname = fname.rsplit(".",1)[0] + "_th.jpg"
        im_th = im_crop.copy(); im_th.thumbnail((420,420), Image.LANCZOS)
        im_th.save(CHAT_THUMB_DIR/tname, "JPEG", quality=85, optimize=True)
    return fname, tname, "image"

class Notification(db.Model):
    __tablename__="notifications"
    id=db.Column(db.Integer, primary_key=True)
    user_id=db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    actor_id=db.Column(db.Integer, db.ForeignKey("users.id"))
    ntype=db.Column(db.String(20))
    photo_id=db.Column(db.Integer, db.ForeignKey("photos.id"))
    comment_id=db.Column(db.Integer, db.ForeignKey("comments.id"))
    created_at=db.Column(db.DateTime, default=dt.datetime.utcnow)
    read=db.Column(db.Boolean, default=False)
    actor=db.relationship("User", foreign_keys=[actor_id])

def notify(recipient_id, actor_id, ntype, photo_id=None, comment_id=None):
    if recipient_id==actor_id: return
    n=Notification(user_id=recipient_id, actor_id=actor_id, ntype=ntype, photo_id=photo_id, comment_id=comment_id)
    db.session.add(n); db.session.commit()

def require_owner(photo):
    if (not current_user.is_authenticated) or photo.user_id!=current_user.id: abort(403)

def get_or_create_thread(uid1, uid2):
    a,b = sorted_pair(uid1, uid2)
    t = ChatThread.query.filter_by(user1_id=a, user2_id=b).first()
    if not t:
        t = ChatThread(user1_id=a, user2_id=b)
        db.session.add(t); db.session.commit()
    return t

# --------- shared helpers at module level ----------
def timeago_ar(ts):
    if not ts: return ""
    delta = dt.datetime.utcnow() - ts
    s = int(delta.total_seconds())
    if s < 45:  return "الآن"
    if s < 90:  return "منذ دقيقة"
    m = s // 60
    if m < 45:  return f"منذ {m} دقيقة" if m==1 else f"منذ {m} دقائق"
    if m < 90:  return "منذ ساعة"
    h = m // 60
    if h < 24:  return f"منذ {h} ساعة"
    d = h // 24
    if d == 1:  return "أمس"
    if d < 30:  return f"منذ {d} يوم"
    mo = d // 30
    if mo < 12: return f"منذ {mo} شهر"
    y = mo // 12
    return f"منذ {y} سنة"

# ======================= Context =======================
@app.context_processor
def inject_globals():
    def format_time(ts): return ts.strftime("%Y/%m/%d %H:%M") if ts else ""
    def get_stats(user):
        if not user: return dict(posts=0,followers=0,following=0,comments=0)
        return dict(
            posts=Photo.query.filter_by(user_id=user.id).count(),
            followers=user.followers.count(),
            following=user.following.count(),
            comments=Comment.query.filter_by(user_id=user.id).count()
        )
    unread = 0
    if current_user.is_authenticated:
        unread = Notification.query.filter_by(user_id=current_user.id, read=False).count()
    return dict(
        now=dt.datetime.utcnow(),
        format_time=format_time,
        timeago_ar=timeago_ar,
        get_stats=get_stats,
        emojis=COMMENT_EMOJIS,
        unread_notifications=unread,
        avatar_url=(current_user.avatar_url if current_user.is_authenticated
                    else url_for("static", filename="avatars/default.png")),
        is_online=is_online
    )

# ======================= Auth =======================
@app.route("/login", methods=["GET","POST"])
def auth_login():
    if request.method=="POST":
        u=request.form.get("username","").strip()
        p=request.form.get("password","")
        user=User.query.filter_by(username=u).first()
        if user and user.check_password(p):
            login_user(user, remember=True)
            flash("تم تسجيل الدخول","success")
            return redirect(request.args.get("next") or url_for("home"))
        flash("بيانات الدخول غير صحيحة","danger")
    return render_template("auth_login.html")

@app.route("/register", methods=["GET","POST"])
def auth_register():
    if request.method=="POST":
        username=request.form.get("username","").strip()
        email=(request.form.get("email","").strip() or None)
        password=request.form.get("password","")
        if not username or not password:
            flash("يرجى كتابة اسم مستخدم وكلمة مرور","warning")
            return render_template("auth_register.html")
        if User.query.filter_by(username=username).first():
            flash("اسم المستخدم محجوز","warning")
            return render_template("auth_register.html")
        user=User(username=username, email=email, display_name=username)
        user.set_password(password)
        db.session.add(user); db.session.commit()
        login_user(user)
        return redirect(url_for("home"))
    return render_template("auth_register.html")

@app.route("/logout")
@login_required
def auth_logout():
    logout_user(); return redirect(url_for("home"))

@app.route("/api/check-username")
def api_check_username():
    u=(request.args.get("u") or "").strip()
    if not USERNAME_RE.match(u):
        return jsonify({"ok": True, "available": False, "reason": "invalid"})
    exists=User.query.filter_by(username=u).first() is not None
    return jsonify({"ok": True, "available": (not exists)})

# ======================= Pages =======================
@app.route("/", endpoint="index")
@app.route("/home", endpoint="home")
def home():
    page=max(int(request.args.get("page",1)),1)
    q=Photo.query.order_by(Photo.created_at.desc())
    photos=q.paginate(page=page, per_page=10, error_out=False)
    return render_template("feed.html", photos=photos.items, pagination=photos)

@app.route("/upload", methods=["GET","POST"])
@login_required
def upload():
    if request.method=="POST":
        files=request.files.getlist("photos")
        if not files or all(not f.filename for f in files):
            flash("اختر صورة واحدة على الأقل","warning")
            return redirect(url_for("upload"))
        caption=request.form.get("caption","").strip()
        tags=request.form.get("tags","").strip()
        allow_comments=bool(request.form.get("allow_comments"))
        allow_share=bool(request.form.get("allow_share"))
        photo=Photo(user_id=current_user.id, caption=caption, tags=tags,
                    allow_comments=allow_comments, allow_share=allow_share)
        db.session.add(photo); db.session.flush()
        saved_any=False
        for f in files[:10]:
            if not f or not f.filename or not allowed_file(f.filename): continue
            saved_any=True
            filename,thumb=save_image(f,"IMG")
            db.session.add(PhotoImage(photo_id=photo.id, filename=filename, thumbfile=thumb))
        if not saved_any:
            db.session.rollback()
            flash("صيغة الملف غير مدعومة","danger")
            return redirect(url_for("upload"))
        db.session.commit()
        flash("تم نشر الصور 👌","success")
        return redirect(url_for("home"))
    return render_template("upload.html")

@app.route("/post/<int:pid>/delete", methods=["POST"])
@login_required
def post_delete(pid):
    p=Photo.query.get_or_404(pid)
    require_owner(p)
    comment_ids=[c.id for c in p.comments]
    if comment_ids:
        Notification.query.filter(Notification.comment_id.in_(comment_ids)).delete(synchronize_session=False)
    Notification.query.filter_by(photo_id=pid).delete(synchronize_session=False)
    if comment_ids:
        CommentReaction.query.filter(CommentReaction.comment_id.in_(comment_ids)).delete(synchronize_session=False)
        Comment.query.filter(Comment.id.in_(comment_ids)).delete(synchronize_session=False)
    Like.query.filter_by(photo_id=pid).delete(synchronize_session=False)
    Bookmark.query.filter_by(photo_id=pid).delete(synchronize_session=False)
    for im in p.images:
        try:
            (UPLOAD_DIR/im.filename).unlink(missing_ok=True)
            (THUMB_DIR/im.thumbfile).unlink(missing_ok=True)
        except Exception: pass
    PhotoImage.query.filter_by(photo_id=pid).delete(synchronize_session=False)
    db.session.delete(p); db.session.commit()
    flash("تم حذف المنشور وكل آثاره.", "info")
    return redirect(request.referrer or url_for("home"))

@app.route("/comment/<int:cid>/like", methods=["POST"])
@login_required
def comment_like(cid):
    c=Comment.query.get_or_404(cid)
    emoji='❤️'
    ex=CommentReaction.query.filter_by(comment_id=cid, user_id=current_user.id, emoji=emoji).first()
    if ex: db.session.delete(ex); on=False
    else:  db.session.add(CommentReaction(comment_id=cid, user_id=current_user.id, emoji=emoji)); on=True
    db.session.commit()
    count=CommentReaction.query.filter_by(comment_id=cid, emoji=emoji).count()
    return jsonify({"ok":True,"on":on,"count":count})

@app.route("/post/<int:pid>/like", methods=["POST"])
@login_required
def post_like(pid):
    p=Photo.query.get_or_404(pid)
    ex=Like.query.filter_by(user_id=current_user.id, photo_id=pid).first()
    if ex: db.session.delete(ex); liked=False
    else:
        db.session.add(Like(user_id=current_user.id, photo_id=pid)); liked=True
        if p.author.notify_likes: notify(p.user_id, current_user.id, "like", photo_id=pid)
    db.session.commit()
    return jsonify({"ok":True,"liked":liked,"count":p.like_count})

@app.route("/post/<int:pid>/bookmark", methods=["POST"])
@login_required
def post_bookmark(pid):
    p=Photo.query.get_or_404(pid)
    ex=Bookmark.query.filter_by(user_id=current_user.id, photo_id=pid).first()
    if ex: db.session.delete(ex); saved=False
    else:  db.session.add(Bookmark(user_id=current_user.id, photo_id=pid)); saved=True
    db.session.commit()
    return jsonify({"ok":True,"saved":saved})

@app.route("/post/<int:pid>/comment", methods=["POST"])
@login_required
def post_comment(pid):
    p=Photo.query.get_or_404(pid)
    if not p.allow_comments: return jsonify({"ok":False,"msg":"التعليقات مغلّقة"}),400
    content=(request.form.get("content") or "").strip()
    if not content: return jsonify({"ok":False,"msg":"أكتب تعليقاً"}),400
    c=Comment(photo_id=pid, user_id=current_user.id, content=content)
    db.session.add(c); db.session.commit()
    if p.author.notify_comments:
        notify(p.user_id, current_user.id, "comment", photo_id=pid, comment_id=c.id)
    return jsonify({"ok":True,
                    "comment":{"id":c.id,"content":c.content,"user":current_user.to_dict(),
                               "created":c.created_at.strftime("%Y/%m/%d %H:%M")},
                    "count":p.comment_count})

@app.route("/u/<username>")
def profile(username):
    user=User.query.filter_by(username=username).first_or_404()
    page=max(int(request.args.get("page",1)),1)
    q=Photo.query.filter_by(user_id=user.id).order_by(Photo.created_at.desc())
    photos=q.paginate(page=page, per_page=9, error_out=False)
    stats=dict(
        posts=q.count(),
        followers=user.followers.count(),
        following=user.following.count(),
        comments=Comment.query.filter_by(user_id=user.id).count()
    )
    return render_template("user_profile.html", user=user, photos=photos.items, stats=stats, pagination=photos)

@app.route("/follow/<username>", methods=["POST"])
@login_required
def follow_toggle(username):
    user=User.query.filter_by(username=username).first_or_404()
    if user.id==current_user.id: return jsonify({"ok":False}),400
    link=Follow.query.filter_by(follower_id=current_user.id, followed_id=user.id).first()
    if link: db.session.delete(link); on=False
    else:
        db.session.add(Follow(follower_id=current_user.id, followed_id=user.id)); on=True
        if user.notify_follows: notify(user.id, current_user.id, "follow")
    db.session.commit()
    return jsonify({"ok":True,"on":on})

@app.route("/saved")
@login_required
def saved():
    page=max(int(request.args.get("page",1)),1)
    ids=[b.photo_id for b in Bookmark.query.filter_by(user_id=current_user.id).all()]
    photos=(Photo.query.filter(Photo.id.in_(ids))
            .order_by(Photo.created_at.desc())
            .paginate(page=page, per_page=10, error_out=False))
    return render_template("saved.html", photos=photos.items, pagination=photos)

@app.route("/my-gallery")
@login_required
def my_gallery():
    page=max(int(request.args.get("page",1)),1)
    q=Photo.query.filter_by(user_id=current_user.id).order_by(Photo.created_at.desc())
    photos=q.paginate(page=page, per_page=12, error_out=False)
    return render_template("my_gallery.html", photos=photos.items, pagination=photos)

# ======================= Chat Pages & APIs =======================
@app.route("/chat")
@login_required
def chat_inbox():
    threads=(ChatThread.query
             .filter((ChatThread.user1_id==current_user.id)|(ChatThread.user2_id==current_user.id))
             .order_by(ChatThread.updated_at.desc()).all())
    threads_info=[]
    for t in threads:
        other_id = t.user2_id if t.user1_id==current_user.id else t.user1_id
        other = User.query.get(other_id)
        threads_info.append({"thread":t, "other":other})
    following_ids=[f.followed_id for f in Follow.query.filter_by(follower_id=current_user.id)]
    users=User.query.filter(User.id.in_(following_ids)).all() if following_ids else []
    return render_template("chat_inbox.html", threads_info=threads_info, users=users)

@app.route("/chat/<username>")
@login_required
def chat_thread(username):
    other=User.query.filter_by(username=username).first_or_404()
    if other.id==current_user.id: return redirect(url_for("chat_inbox"))
    if not can_message(current_user, other):
        flash("لا يمكنك مراسلة هذا المستخدم (يجب أن تتابعه).","warning")
        return redirect(url_for("chat_inbox"))
    thread=get_or_create_thread(current_user.id, other.id)
    msgs=(ChatMessage.query.filter_by(thread_id=thread.id)
          .order_by(ChatMessage.id.asc())
          .limit(100).all())
    unread=(ChatMessage.query.filter_by(thread_id=thread.id)
            .filter(ChatMessage.sender_id!=current_user.id, ChatMessage.read_at.is_(None)).all())
    for m in unread: m.read_at=dt.datetime.utcnow()
    db.session.commit()
    return render_template("chat_thread.html", thread=thread, other=other, messages=msgs)

@app.post("/api/chat/send")
@login_required
def api_chat_send():
    to_username = request.form.get("to")
    thread_id   = request.form.get("thread_id", type=int)
    body        = (request.form.get("body") or "").strip()
    file        = request.files.get("file")

    if not body and not (file and file.filename):
        return jsonify({"ok": False, "msg": "empty"}), 400

    if to_username:
        other = User.query.filter_by(username=to_username).first_or_404()
        if not can_message(current_user, other): return jsonify({"ok": False}), 403
        thread = get_or_create_thread(current_user.id, other.id)
    else:
        thread = ChatThread.query.get_or_404(thread_id)
        if current_user.id not in (thread.user1_id, thread.user2_id): return jsonify({"ok": False}), 403

    att_file = att_thumb = att_type = None
    if file and file.filename:
        saved = save_chat_image(file)
        if not saved: return jsonify({"ok": False, "msg": "نوع الملف غير مدعوم"}), 400
        att_file, att_thumb, att_type = saved

    msg = ChatMessage(
        thread_id=thread.id,
        sender_id=current_user.id,
        body=body if body else None,
        attachment_file=att_file,
        attachment_thumb=att_thumb,
        attachment_type=att_type
    )
    db.session.add(msg)
    thread.updated_at = dt.datetime.utcnow()
    db.session.commit()

    payload = {
        "id": msg.id,
        "body": msg.body or "",
        "created": msg.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "created_human": "الآن",
        "sender": current_user.to_dict()
    }
    if msg.attachment_file:
        payload["attachment"] = {
            "type": msg.attachment_type or "image",
            "url": chat_file_url(msg.attachment_file),
            "thumb": chat_thumb_url(msg.attachment_thumb) if msg.attachment_thumb else None
        }

    return jsonify({"ok": True, "message": payload, "thread_id": thread.id})

@app.route("/api/chat/fetch")
@login_required
def api_chat_fetch():
    thread_id = request.args.get("thread_id", type=int)
    after_id = request.args.get("after_id", default=0, type=int)
    thread = ChatThread.query.get_or_404(thread_id)
    if current_user.id not in (thread.user1_id, thread.user2_id):
        return jsonify({"ok": False}), 403

    q = (ChatMessage.query
         .filter_by(thread_id=thread.id)
         .filter(ChatMessage.id > after_id)
         .order_by(ChatMessage.id.asc()))

    items = []
    for m in q.all():
        msg_data = {
            "id": m.id,
            "body": m.body or "",
            "created": m.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "created_human": timeago_ar(m.created_at),
            "sender": User.query.get(m.sender_id).to_dict()
        }
        if m.attachment_file:
            msg_data["attachment"] = {
                "type": m.attachment_type or "image",
                "url": url_for("static", filename=f"chat_uploads/{m.attachment_file}"),
                "thumb": (url_for("static", filename=f"chat_thumbs/{m.attachment_thumb}")
                          if m.attachment_thumb else url_for("static", filename=f"chat_uploads/{m.attachment_file}"))
            }
        items.append(msg_data)

    # تحديث حالة مقروء
    others = (ChatMessage.query.filter_by(thread_id=thread.id)
              .filter(ChatMessage.sender_id != current_user.id, ChatMessage.read_at.is_(None)).all())
    for m in others:
        m.read_at = dt.datetime.utcnow()
    db.session.commit()

    return jsonify({"ok": True, "messages": items})

# --- Typing indicator (in-memory) ---
GLOBAL_TYPING = {}  # {(thread_id, user_id): timestamp}

@app.post("/api/chat/typing")
@login_required
def api_chat_typing():
    tid=request.form.get("thread_id", type=int)
    if not tid: return jsonify({"ok": False}),400
    t=ChatThread.query.get_or_404(tid)
    if current_user.id not in (t.user1_id, t.user2_id): return jsonify({"ok": False}),403
    GLOBAL_TYPING[(tid, current_user.id)] = dt.datetime.utcnow()
    return jsonify({"ok": True})

@app.get("/api/chat/typing-status")
@login_required
def api_chat_typing_status():
    tid=request.args.get("thread_id", type=int)
    if not tid: return jsonify({"ok": False}),400
    t=ChatThread.query.get_or_404(tid)
    if current_user.id not in (t.user1_id, t.user2_id): return jsonify({"ok": False}),403
    other_id = t.user2_id if current_user.id==t.user1_id else t.user1_id
    ts = GLOBAL_TYPING.get((tid, other_id))
    typing = bool(ts and (dt.datetime.utcnow()-ts).total_seconds()<4)
    return jsonify({"ok": True, "typing": typing})

# --- Notifications pages ---
@app.route("/notifications")
@login_required
def notifications_page():
    items=(Notification.query
           .filter_by(user_id=current_user.id)
           .order_by(Notification.created_at.desc())
           .limit(100).all())
    return render_template("LandPhoto.html", notifications=items)

@app.route("/notifications/mark-read", methods=["POST"])
@login_required
def notifications_mark_read():
    unread=Notification.query.filter_by(user_id=current_user.id, read=False).all()
    for n in unread: n.read=True
    db.session.commit()
    flash("تم تمييز كل الإشعارات كمقروءة","info")
    return redirect(url_for("notifications_page"))

@app.route("/search")
def search():
    q=(request.args.get("q") or "").strip()
    photos=[]; users=[]
    if q:
        users=User.query.filter(User.username.contains(q)).limit(10).all()
        photos=(Photo.query.filter((Photo.caption.contains(q)) | (Photo.tags.contains(q)))
                .order_by(Photo.created_at.desc()).limit(30).all())
    return render_template("feed.html", photos=photos, users=users, search=q)

@app.route("/settings", methods=["GET", "POST"], endpoint="settings")
@login_required
def settings():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "profile":
            if request.form.get("remove_avatar"):
                if current_user.avatar_file:
                    try:
                        (AVATAR_DIR / current_user.avatar_file).unlink(missing_ok=True)
                    except Exception:
                        pass
                current_user.avatar_file = None

            file = request.files.get("avatar")
            if file and file.filename and allowed_file(file.filename):
                fname = make_filename("avatar", file.filename)
                path = AVATAR_DIR / fname
                with Image.open(file.stream) as im:
                    im = im.convert("RGB")
                    w, h = im.size
                    s = min(w, h); l = (w - s)//2; t = (h - s)//2
                    im = im.crop((l, t, l+s, t+s)).resize((512, 512), Image.LANCZOS)
                    im.save(path, "PNG", optimize=True)
                if current_user.avatar_file and current_user.avatar_file != fname:
                    try:
                        (AVATAR_DIR / current_user.avatar_file).unlink(missing_ok=True)
                    except Exception:
                        pass
                current_user.avatar_file = fname

            dn = request.form.get("display_name")
            bio = request.form.get("bio")
            if dn:  current_user.display_name = dn
            if bio: current_user.bio = bio
            db.session.commit()
            flash("تم حفظ الملف الشخصي", "success")

        elif action == "password":
            old = request.form.get("old_password","")
            new = request.form.get("new_password","")
            confirm = request.form.get("confirm_password","")
            if not current_user.check_password(old):
                flash("كلمة المرور الحالية غير صحيحة", "danger")
            elif len(new) < 6 or new != confirm:
                flash("تأكد من كلمة المرور الجديدة", "warning")
            else:
                current_user.set_password(new)
                db.session.commit()
                flash("تم تحديث كلمة المرور", "success")

        elif action == "notifications":
            current_user.notify_likes    = bool(request.form.get("notify_likes"))
            current_user.notify_comments = bool(request.form.get("notify_comments"))
            current_user.notify_follows  = bool(request.form.get("notify_follows"))
            db.session.commit()
            flash("تم حفظ تفضيلات الإشعارات", "success")

        return redirect(url_for("settings"))

    return render_template("settings.html")

# ======================= Errors & Filters =======================
@app.errorhandler(403)
def e403(e): return render_template("base.html", content="ليس لديك صلاحية"),403
@app.errorhandler(404)
def e404(e): return render_template("base.html", content="الصفحة غير موجودة"),404

@app.template_filter("nl2br")
def nl2br(s): return "" if not s else s.replace("\n","<br>")

# ======================= DB init & migrations =======================
def init_demo_user():
    if not User.query.filter_by(username="admin").first():
        u=User(username="admin", display_name="Admin")
        u.set_password("admin123")
        db.session.add(u); db.session.commit()

def run_startup_migrations():
    # إضافة أعمدة مرفقات الدردشة إن لم تكن موجودة (SQLite)
    with db.engine.connect() as conn:
        rows = conn.exec_driver_sql("PRAGMA table_info(chat_messages)").fetchall()
        existing = {row[1] for row in rows}
        if "attachment_file" not in existing:
            conn.exec_driver_sql("ALTER TABLE chat_messages ADD COLUMN attachment_file VARCHAR(255)")
        if "attachment_thumb" not in existing:
            conn.exec_driver_sql("ALTER TABLE chat_messages ADD COLUMN attachment_thumb VARCHAR(255)")
        if "attachment_type" not in existing:
            conn.exec_driver_sql("ALTER TABLE chat_messages ADD COLUMN attachment_type VARCHAR(20)")

with app.app_context():
    db.create_all()
    run_startup_migrations()
    init_demo_user()

# ======================= GIPHY Proxy =======================
@app.get("/api/giphy/trending")
@login_required
def giphy_trending():
    limit = request.args.get("limit", 18, type=int)
    params = {"api_key": GIPHY_API_KEY, "limit": limit, "rating": "g"}
    r = requests.get("https://api.giphy.com/v1/gifs/trending", params=params, timeout=10)
    return jsonify(r.json()), r.status_code

@app.get("/api/giphy/search")
@login_required
def giphy_search():
    q = request.args.get("q", "", type=str)
    limit = request.args.get("limit", 18, type=int)
    params = {"api_key": GIPHY_API_KEY, "q": q, "limit": limit, "rating": "g", "lang": "ar"}
    r = requests.get("https://api.giphy.com/v1/gifs/search", params=params, timeout=10)
    return jsonify(r.json()), r.status_code

# === PWA: service worker at site root ===
from flask import send_from_directory

@app.route("/service-worker.js")
def service_worker():
    # يجب أن يكون في الجذر، لذا نرسله من مجلد static
    return send_from_directory("static", "pwa/service-worker.js",
                               mimetype="application/javascript")
# ======================= Run =======================
if __name__=="__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
