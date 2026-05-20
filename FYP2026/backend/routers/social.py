from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.auth import get_current_user
from backend.database import get_db

router = APIRouter()


# ── Posts ─────────────────────────────────────────────────────────────────────

@router.post("/posts", response_model=schemas.SocialPostOut, status_code=201)
def create_post(
    body: schemas.SocialPostCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not current_user.allow_social_sharing:
        raise HTTPException(status_code=403, detail="Social sharing is disabled in your privacy settings")

    post = models.SocialPost(
        user_id=current_user.id,
        post_type=body.post_type,
        caption=body.caption,
        session_id=body.session_id,
        achievement_id=body.achievement_id,
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    return schemas.SocialPostOut(
        id=post.id,
        post_type=post.post_type,
        image_url=post.image_url,
        caption=post.caption,
        likes=post.likes,
        created_at=post.created_at,
        username=current_user.username,
        profile_photo=current_user.profile_photo,
    )


@router.get("/feed", response_model=list[schemas.SocialPostOut])
def get_feed(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Get posts from followed users + own posts
    following_ids = [
        f.followee_id for f in db.query(models.Follower).filter(
            models.Follower.follower_id == current_user.id
        ).all()
    ]
    following_ids.append(current_user.id)

    posts = (
        db.query(models.SocialPost)
        .filter(models.SocialPost.user_id.in_(following_ids))
        .order_by(models.SocialPost.created_at.desc())
        .limit(limit)
        .all()
    )

    result = []
    for post in posts:
        user = db.get(models.User, post.user_id)
        result.append(schemas.SocialPostOut(
            id=post.id,
            post_type=post.post_type,
            image_url=post.image_url,
            caption=post.caption,
            likes=post.likes,
            created_at=post.created_at,
            username=user.username if user else "Unknown",
            profile_photo=user.profile_photo if user else None,
        ))
    return result


@router.get("/explore", response_model=list[schemas.SocialPostOut])
def explore_posts(
    limit: int = 30,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    posts = (
        db.query(models.SocialPost)
        .join(models.User, models.SocialPost.user_id == models.User.id)
        .filter(models.User.is_public_profile == True)
        .order_by(models.SocialPost.created_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for post in posts:
        user = db.get(models.User, post.user_id)
        result.append(schemas.SocialPostOut(
            id=post.id,
            post_type=post.post_type,
            image_url=post.image_url,
            caption=post.caption,
            likes=post.likes,
            created_at=post.created_at,
            username=user.username if user else "Unknown",
            profile_photo=user.profile_photo if user else None,
        ))
    return result


@router.post("/posts/{post_id}/like", response_model=dict)
def like_post(
    post_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    post = db.get(models.SocialPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post.likes += 1
    db.commit()
    return {"likes": post.likes}


@router.delete("/posts/{post_id}", status_code=204)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    post = db.get(models.SocialPost, post_id)
    if not post or post.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Post not found")
    db.delete(post)
    db.commit()


# ── Followers ─────────────────────────────────────────────────────────────────

@router.post("/follow/{user_id}", status_code=201, response_model=dict)
def follow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")

    target = db.get(models.User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(models.Follower).filter(
        models.Follower.follower_id == current_user.id,
        models.Follower.followee_id == user_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Already following")

    follow = models.Follower(follower_id=current_user.id, followee_id=user_id)
    db.add(follow)

    notif = models.Notification(
        user_id=user_id,
        type="social",
        content=f"{current_user.username} started following you!",
    )
    db.add(notif)
    db.commit()
    return {"message": f"Now following {target.username}"}


@router.delete("/follow/{user_id}", status_code=204)
def unfollow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    follow = db.query(models.Follower).filter(
        models.Follower.follower_id == current_user.id,
        models.Follower.followee_id == user_id,
    ).first()
    if not follow:
        raise HTTPException(status_code=404, detail="Not following this user")
    db.delete(follow)
    db.commit()


@router.get("/followers", response_model=list[dict])
def my_followers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rows = db.query(models.Follower).filter(
        models.Follower.followee_id == current_user.id
    ).all()
    result = []
    for row in rows:
        u = db.get(models.User, row.follower_id)
        if u:
            result.append({
                "user_id": u.id,
                "username": u.username,
                "profile_photo": u.profile_photo,
                "level": u.level,
                "total_points": u.total_points,
            })
    return result


@router.get("/following", response_model=list[dict])
def my_following(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rows = db.query(models.Follower).filter(
        models.Follower.follower_id == current_user.id
    ).all()
    result = []
    for row in rows:
        u = db.get(models.User, row.followee_id)
        if u:
            result.append({
                "user_id": u.id,
                "username": u.username,
                "profile_photo": u.profile_photo,
                "level": u.level,
                "total_points": u.total_points,
            })
    return result


# ── Favorites ─────────────────────────────────────────────────────────────────

@router.post("/favorites/{exercise_id}", status_code=201, response_model=dict)
def add_favorite(
    exercise_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ex = db.get(models.ExerciseLibrary, exercise_id)
    if not ex:
        raise HTTPException(status_code=404, detail="Exercise not found")
    existing = db.query(models.Favorite).filter(
        models.Favorite.user_id == current_user.id,
        models.Favorite.exercise_id == exercise_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Already in favorites")
    fav = models.Favorite(user_id=current_user.id, exercise_id=exercise_id)
    db.add(fav)
    db.commit()
    return {"message": "Added to favorites"}


@router.delete("/favorites/{exercise_id}", status_code=204)
def remove_favorite(
    exercise_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    fav = db.query(models.Favorite).filter(
        models.Favorite.user_id == current_user.id,
        models.Favorite.exercise_id == exercise_id,
    ).first()
    if not fav:
        raise HTTPException(status_code=404, detail="Not in favorites")
    db.delete(fav)
    db.commit()


@router.get("/favorites", response_model=list[schemas.FavoriteOut])
def list_favorites(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Favorite)
        .filter(models.Favorite.user_id == current_user.id)
        .all()
    )
