import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError

# --- App Configuration ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_very_secret_key_that_should_be_changed'

# --- Database Configuration ---
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Use the Render PostgreSQL database
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    # Fallback to local SQLite database for development
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'site.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
login_manager.login_message = "יש להתחבר כדי לגשת לעמוד זה."


# --- Models ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def __repr__(self):
        return f"User('{self.email}')"

class Deal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    old_price = db.Column(db.String(20), nullable=True)
    new_price = db.Column(db.String(20), nullable=False)
    image_url = db.Column(db.String(200), nullable=True)
    deal_link = db.Column(db.String(200), nullable=False)
    coupon_code = db.Column(db.String(50), nullable=True)
    category = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f"Deal('{self.title}', '{self.new_price}')"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Forms ---
class RegistrationForm(FlaskForm):
    email = StringField('אימייל', validators=[DataRequired(), Email(message="כתובת אימייל לא תקינה.")])
    password = PasswordField('סיסמה', validators=[DataRequired()])
    confirm_password = PasswordField('אימות סיסמה', validators=[DataRequired(), EqualTo('password', message='הסיסמאות חייבות להיות זהות.')])
    submit = SubmitField('הרשמה')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('כתובת האימייל הזו כבר קיימת במערכת.')

class LoginForm(FlaskForm):
    email = StringField('אימייל', validators=[DataRequired(), Email()])
    password = PasswordField('סיסמה', validators=[DataRequired()])
    submit = SubmitField('התחברות')


# --- Routes ---
@app.route('/')
def index():
    category_filter = request.args.get('category')
    if category_filter:
        deals = Deal.query.filter_by(category=category_filter).all()
    else:
        deals = Deal.query.all()
    
    categories = sorted(list(set(d.category for d in Deal.query.all())))
    
    return render_template('index.html', deals=deals, categories=categories, current_category=category_filter)

@app.route('/deal-expired')
def deal_expired():
    return render_template('deal_expired.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        user = User(email=form.email.data, password_hash=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('החשבון נוצר בהצלחה! כעת ניתן להתחבר.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            flash('התחברת בהצלחה!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('התחברות נכשלה. בדוק אימייל וסיסמה.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('התנתקת בהצלחה.', 'success')
    return redirect(url_for('index'))

@app.cli.command('init-db')
def init_db_command():
    """Creates the database tables and populates them with initial data."""
    db.drop_all()
    db.create_all()

    if Deal.query.first() is None:
        deals_data = [
            # קטגוריה: מחשבים וציוד היקפי
            {'title': 'כרטיס מסך GeForce RTX 4070', 'description': 'KSP - כרטיס מסך עוצמתי לגיימינג.', 'old_price': '3,500 ₪', 'new_price': '2,899 ₪', 'deal_link': '#', 'coupon_code': 'MEGA150', 'category': 'מחשבים וציוד היקפי'},
            {'title': 'כיסא גיימינג Secretlab Titan', 'description': 'הכיסא האולטימטיבי לגיימרים וליוצרי תוכן.', 'old_price': '2,500 ₪', 'new_price': '2,100 ₪', 'deal_link': '#', 'coupon_code': 'GAMINGX', 'category': 'מחשבים וציוד היקפי'},
            {'title': 'מסך מחשב Dell UltraSharp U2723QE', 'description': 'מסך 4K עם דיוק צבעים מדהים למקצוענים.', 'old_price': '3,800 ₪', 'new_price': '3,100 ₪', 'deal_link': '#', 'coupon_code': 'DELLPRO', 'category': 'מחשבים וציוד היקפי'},
            {'title': 'מקלדת מכנית Logitech MX Mechanical', 'description': 'מקלדת אלחוטית, שקטה ומדויקת.', 'old_price': '700 ₪', 'new_price': '550 ₪', 'deal_link': '#', 'coupon_code': 'LOGI20', 'category': 'מחשבים וציוד היקפי'},
            
            # קטגוריה: אוזניות וסאונד
            {'title': 'אוזניות Sony WH-1000XM5', 'description': 'Amazon US - מבטלות רעשים מהטובות בעולם.', 'old_price': '1,800 ₪', 'new_price': '1,250 ₪', 'deal_link': '#', 'coupon_code': 'SONYDEAL', 'category': 'אוזניות וסאונד'},
            {'title': 'רמקול Bluetooth נייד JBL Flip 6', 'description': 'רמקול עמיד למים עם סאונד עוצמתי.', 'old_price': '500 ₪', 'new_price': '380 ₪', 'deal_link': '#', 'coupon_code': 'JBLFLIP', 'category': 'אוזניות וסאונד'},
            
            # קטגוריה: מוצרי חשמל לבית
            {'title': 'שואב אבק Roborock S8', 'description': 'Aliexpress - הדור החדש של השואבים הרובוטיים.', 'old_price': '3,200 ₪', 'new_price': '2,450 ₪', 'deal_link': '#', 'coupon_code': 'MEGA200', 'category': 'מוצרי חשמל לבית'},
            {'title': 'מכונת קפה Nespresso', 'description': 'LastPrice - מכונת קפה מעוצבת ואיכותית.', 'old_price': '800 ₪', 'new_price': '550 ₪', 'deal_link': '#', 'coupon_code': 'COFFEE10', 'category': 'מוצרי חשמל לבית'},
            {'title': 'בלנדר מוט Braun MultiQuick 9', 'description': 'בלנדר עוצמתי עם שלל אביזרים נלווים.', 'old_price': '600 ₪', 'new_price': '450 ₪', 'deal_link': '#', 'coupon_code': 'BRAUN25', 'category': 'מוצרי חשמל לבית'},
            {'title': 'מטהר אוויר Xiaomi Smart Air Purifier 4', 'description': 'שומר על אוויר נקי בבית, שליטה מהאפליקציה.', 'old_price': '750 ₪', 'new_price': '600 ₪', 'deal_link': '#', 'coupon_code': 'AIRPURE', 'category': 'מוצרי חשמל לבית'},

            # קטגוריה: ספורט וטיולים
            {'title': 'נעלי ריצה ASICS Gel-Kayano', 'description': 'Amazon DE - נעלי ריצה מקצועיות למרחקים.', 'old_price': '750 ₪', 'new_price': '580 ₪', 'deal_link': '#', 'coupon_code': 'RUN4U', 'category': 'ספורט וטיולים'},
            {'title': 'שעון חכם Garmin Fenix 7', 'description': 'שעון ספורט מתקדם עם GPS ומפות מובנות.', 'old_price': '3,000 ₪', 'new_price': '2,550 ₪', 'deal_link': '#', 'coupon_code': 'GARMIN15', 'category': 'ספורט וטיולים'},
            {'title': 'תרמיל טיולים Osprey Atmos AG 65', 'description': 'תרמיל נוח ומאוורר לטרקים ארוכים.', 'old_price': '1,200 ₪', 'new_price': '950 ₪', 'deal_link': '#', 'coupon_code': 'OSPREY10', 'category': 'ספורט וטיולים'},

            # קטגוריה: סלולר
            {'title': 'סמארטפון Samsung Galaxy S24', 'description': 'Ivory - מכשיר הדגל החדש של סמסונג.', 'old_price': '4,200 ₪', 'new_price': '3,800 ₪', 'deal_link': '#', 'coupon_code': 'GALAXY5', 'category': 'סלולר'},
            {'title': 'מטען נייד Anker PowerCore 20000', 'description': 'סוללה ניידת עוצמתית עם טעינה מהירה.', 'old_price': '250 ₪', 'new_price': '180 ₪', 'deal_link': '#', 'coupon_code': 'ANKERDEAL', 'category': 'סלולר'},
            {'title': 'מגן מסך Spigen Glas.tR EZ Fit', 'description': 'מגן זכוכית איכותי עם התקנה קלה.', 'old_price': '120 ₪', 'new_price': '80 ₪', 'deal_link': '#', 'coupon_code': 'SPIGEN10', 'category': 'סלולר'},

            # קטגוריה: טיפוח ויופי
            {'title': 'מכונת גילוח Philips Series 9000', 'description': 'גילוח צמוד ונוח, מתאים לעור רגיש.', 'old_price': '900 ₪', 'new_price': '650 ₪', 'deal_link': '#', 'coupon_code': 'SHAVEUP', 'category': 'טיפוח ויופי'},
            {'title': 'מייבש שיער Dyson Supersonic', 'description': 'מייבש שיער מהיר ושקט, מונע נזקי חום.', 'old_price': '2,000 ₪', 'new_price': '1,650 ₪', 'deal_link': '#', 'coupon_code': 'DYSON100', 'category': 'טיפוח ויופי'},
            
            # קטגוריה: לילדים
            {'title': 'סט לגו Star Wars Millennium Falcon', 'description': 'סט הרכבה אייקוני לאספנים וחובבי הסדרה.', 'old_price': '800 ₪', 'new_price': '680 ₪', 'deal_link': '#', 'coupon_code': 'LEGOFUN', 'category': 'לילדים'},
            {'title': 'בוסטר לרכב Graco TurboBooster', 'description': 'מושב בטיחות נוח ובטוח לילדים.', 'old_price': '350 ₪', 'new_price': '250 ₪', 'deal_link': '#', 'coupon_code': 'GRACOKID', 'category': 'לילדים'},
        ]
        for deal_info in deals_data:
            deal = Deal(**deal_info)
            db.session.add(deal)
        
        db.session.commit()
        print("Database seeded with new sample deals.")

if __name__ == '__main__':
    app.run(debug=True, port=5002) 