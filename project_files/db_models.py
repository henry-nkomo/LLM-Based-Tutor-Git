from . import db

class trackProgress(db.Model):
    __tablename__ = 'track_progress'

    # Primary key
    progress_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Foreign key to user
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user_credentials.id', ondelete='CASCADE'),
        nullable=False,
        unique=True   # ensures 1-to-1 relationship
    )

    # Preferences (VARCHAR, as decided)
    report_summary = db.Column(db.String(255), nullable=False, default="")

    # JSON fields
    skills_component = db.Column(db.JSON, nullable=False, default=dict)

    # Relationships
    user = db.relationship('Users', back_populates='progress')


class Users(db.Model):
    __tablename__ = 'user_credentials'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)  
    email = db.Column(db.String(100), nullable=False, unique=True)  
    password = db.Column(db.String(255), nullable=False)

    progress = db.relationship(
        'trackProgress',
        back_populates='user',
        uselist=False,               
        cascade='all, delete-orphan'
    )
    
    def __repr__(self):
        return f'<User {self.name}>'