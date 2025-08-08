import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime
import hashlib
import os
import tempfile
from pathlib import Path
from typing import Optional

# ----------------------
# Configuration
# ----------------------
DB_PATH = "ideas_app.db"
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# ----------------------
# Database setup
# ----------------------
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String(120))
    email = Column(String(200), unique=True, index=True)
    password_hash = Column(String(128))
    bio = Column(Text, default='')
    is_admin = Column(Boolean, default=False)
    badge = Column(String(120), nullable=True)  # e.g. 'Verified Expert', 'Veteran', 'Journalist'
    created_at = Column(DateTime, default=datetime.utcnow)
    ideas = relationship('Idea', back_populates='author')

class Idea(Base):
    __tablename__ = 'ideas'
    id = Column(Integer, primary_key=True)
    title = Column(String(250))
    description = Column(Text)
    tags = Column(String(250))
    created_at = Column(DateTime, default=datetime.utcnow)
    author_id = Column(Integer, ForeignKey('users.id'))
    attachments = Column(String(1000), nullable=True)  # comma separated file paths
    priority = Column(Boolean, default=False)  # awarded to badged / prioritized ideas
    author = relationship('User', back_populates='ideas')
    avg_rating = Column(Float, default=0.0)
    upvotes = Column(Integer, default=0)

class Review(Base):
    __tablename__ = 'reviews'
    id = Column(Integer, primary_key=True)
    idea_id = Column(Integer, ForeignKey('ideas.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    rating = Column(Integer)
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class VerificationRequest(Base):
    __tablename__ = 'verifications'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    claim = Column(String(250))
    details = Column(Text)
    proof_files = Column(String(1000))  # comma separated file paths
    status = Column(String(50), default='pending')  # pending, approved, rejected
    admin_note = Column(Text, nullable=True)
    requested_at = Column(DateTime, default=datetime.utcnow)

# Create engine + session
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

# ----------------------
# Utility functions
# ----------------------

def get_session():
    return SessionLocal()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def save_uploaded_file(uploaded_file) -> str:
    suffix = Path(uploaded_file.name).suffix
    dest = UPLOAD_DIR / f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{uploaded_file.name}"
    with open(dest, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    return str(dest)


def current_user() -> Optional[User]:
    sess = get_session()
    uid = st.session_state.get('user_id')
    if not uid:
        return None
    return sess.query(User).filter(User.id == uid).first()

# ----------------------
# Styling
# ----------------------

st.set_page_config(page_title='Ideas for Palestine — Share · Rate · Verify', layout='wide')

APP_CSS = '''
<style>
body { background: linear-gradient(120deg,#fdfbfb 0%,#ebedee 100%); }
.app-header{display:flex;align-items:center;gap:16px}
.brand{font-size:26px;font-weight:700}
.card{background:white;padding:18px;border-radius:12px;box-shadow:0 6px 18px rgba(0,0,0,0.06);}
.tag{display:inline-block;padding:6px 10px;border-radius:999px;border:1px solid #eee;margin-right:6px}
.badge {background:linear-gradient(90deg,#ffd54d,#ff8a65);padding:6px 10px;border-radius:999px;color:#222;font-weight:600}
.small{font-size:13px;color:#555}
</style>
'''
st.markdown(APP_CSS, unsafe_allow_html=True)

# ----------------------
# Sidebar - navigation + auth
# ----------------------
with st.sidebar:
    st.markdown('<div class="app-header"><div class="brand">أفكار لدعم فلسطين</div></div>', unsafe_allow_html=True)
    menu = st.radio('Navigation', ['Home', 'Submit Idea', 'Verify Identity', 'My Profile', 'Admin Panel' if st.session_state.get('is_admin') else ''])
    if menu == '':
        menu = 'Home'

    st.markdown('---')
    # Auth widget
    if 'user_id' not in st.session_state or st.session_state.get('user_id') is None:
        with st.expander('Se connecter / S'inscrire'):
            mode = st.selectbox('Mode', ['Login', 'Register'])
            if mode == 'Register':
                name = st.text_input('Nom complet')
                email = st.text_input('Adresse email')
                password = st.text_input('Mot de passe', type='password')
                bio = st.text_area('Bio courte (optionnel)')
                if st.button('S'inscrire'):
                    if not name or not email or not password:
                        st.error('Veuillez remplir nom, email et mot de passe')
                    else:
                        sess = get_session()
                        if sess.query(User).filter(User.email == email).first():
                            st.error('Un compte avec cet email existe déjà')
                        else:
                            u = User(name=name, email=email, password_hash=hash_password(password), bio=bio)
                            sess.add(u)
                            sess.commit()
                            st.success('Compte créé — vous pouvez maintenant vous connecter')
            else:
                email = st.text_input('Email', key='login_email')
                password = st.text_input('Mot de passe', type='password', key='login_pw')
                if st.button('Se connecter'):
                    sess = get_session()
                    user = sess.query(User).filter(User.email == email).first()
                    if not user or user.password_hash != hash_password(password):
                        st.error('Email ou mot de passe incorrect')
                    else:
                        st.session_state['user_id'] = user.id
                        st.session_state['is_admin'] = bool(user.is_admin)
                        st.success(f'Bienvenue, {user.name}!')
    else:
        user = current_user()
        st.markdown(f"**Connecté en tant que**\n\n**{user.name}**\n\n<span class='small'>{user.email}</span>", unsafe_allow_html=True)
        if user.badge:
            st.markdown(f"<div class='badge'>{user.badge}</div>", unsafe_allow_html=True)
        if st.button('Se déconnecter'):
            st.session_state.pop('user_id', None)
            st.session_state.pop('is_admin', None)
            st.experimental_rerun()

# ----------------------
# Page implementations
# ----------------------

def render_home():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header('Idées pour aider la Palestine — partageons, discutons, priorisons')
    st.markdown('Nous accueillons des idées concrètes — humanitaires, logistiques, médiatiques, de plaidoyer et d\'innovation. Les idées vérifiées par des experts ou personnes reconnues seront signalées par un badge et priorisées.')
    st.markdown('</div>', unsafe_allow_html=True)

    sess = get_session()
    q = sess.query(Idea).all()

    # Sorting: priority first, then by score (avg_rating + upvotes weight)
    def score(i: Idea):
        return (1 if i.priority else 0) * 100 + (i.avg_rating * 10) + i.upvotes

    ideas = sorted(q, key=lambda x: score(x), reverse=True)

    col1, col2 = st.columns([2,1])
    with col1:
        for idea in ideas:
            author = sess.query(User).filter(User.id == idea.author_id).first()
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"### {idea.title}")
            if author and author.badge:
                st.markdown(f"<div class='badge'> {author.badge} — {author.name}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='small'>Par <b>{author.name if author else 'Utilisateur supprimé'}</b> — {idea.created_at.strftime('%Y-%m-%d')}</div>", unsafe_allow_html=True)
            st.markdown(f"{idea.description}")
            if idea.tags:
                tags_html = ' '.join([f"<span class='tag'>{t.strip()}</span>" for t in idea.tags.split(',') if t.strip()])
                st.markdown(tags_html, unsafe_allow_html=True)

            st.markdown(f"**Note moyenne:** {idea.avg_rating:.1f} — **Upvotes:** {idea.upvotes}")

            if idea.attachments:
                files = idea.attachments.split(',')
                for f in files:
                    st.markdown(f"- Fichier: {os.path.basename(f)}")
            if st.button('Voir & Réagir', key=f'view_{idea.id}'):
                st.session_state['view_idea'] = idea.id
                st.experimental_rerun()

            st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader('Recherche & filtres')
        qtxt = st.text_input('Chercher un mot-clé...')
        tag_filter = st.text_input('Filtrer par tag (comma separated)')
        min_rating = st.slider('Note min', 0.0, 5.0, 0.0)
        if st.button('Appliquer filtre'):
            # simple filter: just re-query and present matches
            filtered = []
            for idea in ideas:
                if qtxt.lower() in (idea.title + ' ' + idea.description).lower() and idea.avg_rating >= min_rating:
                    if tag_filter:
                        tags = [t.strip().lower() for t in tag_filter.split(',')]
                        idea_tags = [t.strip().lower() for t in (idea.tags or '').split(',')]
                        if any(t in idea_tags for t in tags):
                            filtered.append(idea)
                    else:
                        filtered.append(idea)
            st.write(f'{len(filtered)} résultats')
            for idea in filtered:
                st.write(f"- {idea.title} — {idea.avg_rating:.1f} — {idea.upvotes} upvotes")
        st.markdown('</div>', unsafe_allow_html=True)

    # If user clicked View & React
    if st.session_state.get('view_idea'):
        idea_id = st.session_state.get('view_idea')
        idea = sess.query(Idea).filter(Idea.id == idea_id).first()
        if idea:
            st_markdown_view_idea(idea)


def st_markdown_view_idea(idea: Idea):
    sess = get_session()
    st.markdown('<div class="card">', unsafe_allow_html=True)
    author = sess.query(User).filter(User.id == idea.author_id).first()
    st.subheader(idea.title)
    if author and author.badge:
        st.markdown(f"<div class='badge'>{author.badge} — {author.name}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='small'>Par <b>{author.name if author else 'Utilisateur supprimé'}</b> — {idea.created_at.strftime('%Y-%m-%d')}</div>", unsafe_allow_html=True)
    st.write(idea.description)
    st.write('Tags:', idea.tags)
    st.write('Note moyenne:', f"{idea.avg_rating:.1f}")
    st.write('Upvotes:', idea.upvotes)

    if st.button('Upvote cette idée', key=f'up_{idea.id}'):
        idea.upvotes += 1
        sess.add(idea)
        sess.commit()
        st.experimental_rerun()

    # Reviews
    st.markdown('---')
    st.write('Commentaires & notes')
    reviews = sess.query(Review).filter(Review.idea_id == idea.id).order_by(Review.created_at.desc()).all()
    for r in reviews:
        u = sess.query(User).filter(User.id == r.user_id).first()
        st.markdown(f"**{u.name if u else 'Utilisateur supprimé'}** — {r.rating}/5 — {r.created_at.strftime('%Y-%m-%d')}")
        st.write(r.comment)
    st.markdown('---')
    if current_user():
        rating = st.slider('Votre note', 1, 5, 5, key=f'rating_{idea.id}')
        comment = st.text_area('Votre commentaire', key=f'comment_{idea.id}')
        if st.button('Poster commentaire', key=f'post_{idea.id}'):
            r = Review(idea_id=idea.id, user_id=current_user().id, rating=rating, comment=comment)
            sess.add(r)
            # update aggregated rating
            all_r = sess.query(Review).filter(Review.idea_id == idea.id).all()
            sess.commit()
            avg = sum([x.rating for x in all_r]) / len(all_r)
            idea.avg_rating = avg
            sess.add(idea)
            sess.commit()
            st.success('Merci pour votre retour')
            st.experimental_rerun()
    else:
        st.info('Connectez-vous pour laisser une note ou commentaire')

    st.markdown('</div>', unsafe_allow_html=True)


def render_submit_idea():
    st.header('Soumettre une idée')
    if not current_user():
        st.info('Veuillez vous connecter pour soumettre une idée')
        return
    title = st.text_input('Titre')
    desc = st.text_area('Description (décrivez le comment, le pourquoi, le besoin, l\'impact)')
    tags = st.text_input('Tags (comma separated)')
    uploads = st.file_uploader('Ajouter des fichiers (preuves, images, documents) — optionnel', accept_multiple_files=True)
    if st.button('Soumettre'):
        if not title or not desc:
            st.error('Titre et description sont requis')
        else:
            files_saved = []
            for u in uploads:
                files_saved.append(save_uploaded_file(u))
            sess = get_session()
            idea = Idea(title=title, description=desc, tags=tags, author_id=current_user().id, attachments=','.join(files_saved))
            # If author has a badge, mark priority
            if current_user().badge:
                idea.priority = True
            sess.add(idea)
            sess.commit()
            st.success('Idée soumise — merci!')


def render_verify_identity():
    st.header('Demander une vérification de profil (pour badge)')
    if not current_user():
        st.info('Veuillez vous connecter pour demander une vérification')
        return
    st.write('Si vous vous déclarez comme ayant une expertise, un grade militaire, un rôle de premier plan ou une expérience vérifiable liée au soutien humanitaire / défense / logistique — vous pouvez demander une vérification.')
    claim = st.text_input('Votre revendication (ex: Sergent, Expert en Logistique Humanitaire, Journaliste)')
    details = st.text_area('Détails (expérience, organisation, lien, contact pour vérification)')
    proofs = st.file_uploader('Preuves (carte d\'identité professionnelle, certificats, lettres) — multiples autorisés', accept_multiple_files=True)
    if st.button('Soumettre la demande de vérification'):
        if not claim or not details:
            st.error('Veuillez décrire votre revendication et fournir des détails')
        else:
            files_saved = []
            for f in proofs:
                files_saved.append(save_uploaded_file(f))
            sess = get_session()
            req = VerificationRequest(user_id=current_user().id, claim=claim, details=details, proof_files=','.join(files_saved), status='pending')
            sess.add(req)
            sess.commit()
            st.success('Demande envoyée — un administrateur examinera vos documents')


def render_profile():
    user = current_user()
    if not user:
        st.info('Connectez-vous pour accéder à votre profil')
        return
    st.header('Mon profil')
    st.markdown(f"**{user.name}** — {user.email}")
    st.write(user.bio)
    st.write('Badge:', user.badge or 'Aucun')
    sess = get_session()
    ideas = sess.query(Idea).filter(Idea.author_id == user.id).all()
    st.subheader('Mes idées')
    for idea in ideas:
        st.write(f"- {idea.title} — {idea.avg_rating:.1f} — upvotes {idea.upvotes}")


def render_admin_panel():
    user = current_user()
    if not user or not user.is_admin:
        st.info('Panneau d\'administration réservé aux administrateurs')
        return
    st.header('Admin panel — Vérifications & Modération')
    sess = get_session()
    st.subheader('Demandes de vérification en attente')
    pending = sess.query(VerificationRequest).filter(VerificationRequest.status == 'pending').all()
    for r in pending:
        u = sess.query(User).filter(User.id == r.user_id).first()
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f"**{u.name}** — Claim: {r.claim}")
        st.write(r.details)
        if r.proof_files:
            for f in r.proof_files.split(','):
                st.write('-', os.path.basename(f))
        if st.button('Approuver', key=f'appr_{r.id}'):
            # award a badge to user
            u.badge = r.claim + ' (Vérifié)'
            r.status = 'approved'
            r.admin_note = 'Approved by admin'
            # set priority to all user's ideas
            for idea in u.ideas:
                idea.priority = True
                sess.add(idea)
            sess.add(u)
            sess.add(r)
            sess.commit()
            st.success('Vérification approuvée et badge attribué')
            st.experimental_rerun()
        if st.button('Rejeter', key=f'rej_{r.id}'):
            r.status = 'rejected'
            r.admin_note = 'Rejected by admin'
            sess.add(r)
            sess.commit()
            st.success('Demande rejetée')
            st.experimental_rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.subheader('Gestion des idées')
    all_ideas = sess.query(Idea).order_by(Idea.created_at.desc()).all()
    for idea in all_ideas[:30]:
        author = sess.query(User).filter(User.id == idea.author_id).first()
        st.write(f"{idea.id} — {idea.title} — by {author.name if author else '—'} — priority: {idea.priority}")
        cols = st.columns(3)
        if cols[0].button('Supprimer', key=f'del_{idea.id}'):
            sess.delete(idea)
            sess.commit()
            st.experimental_rerun()
        if cols[1].button('Marquer prioritaire', key=f'pr_{idea.id}'):
            idea.priority = True
            sess.add(idea)
            sess.commit()
            st.experimental_rerun()
        if cols[2].button('Retirer priorité', key=f'unpr_{idea.id}'):
            idea.priority = False
            sess.add(idea)
            sess.commit()
            st.experimental_rerun()

# ----------------------
# Router
# ----------------------
page = menu
if page == 'Home':
    render_home()
elif page == 'Submit Idea':
    render_submit_idea()
elif page == 'Verify Identity':
    render_verify_identity()
elif page == 'My Profile':
    render_profile()
elif page == 'Admin Panel' and st.session_state.get('is_admin'):
    render_admin_panel()

# ----------------------
# On first run: create an admin account if none exists
# ----------------------
sess = get_session()
if not sess.query(User).filter(User.is_admin == True).first():
    admin_pw = 'adminpass'  # change after first login
    admin = User(name='Admin', email='admin@example.com', password_hash=hash_password(admin_pw), is_admin=True)
    sess.add(admin)
    sess.commit()
    st.info('Admin user created: admin@example.com / adminpass — change immediately')
