from aiogram.fsm.state import State, StatesGroup


class AddAnime(StatesGroup):
    title = State()
    description = State()
    genre = State()
    year = State()
    poster = State()


class AddEpisode(StatesGroup):
    choose_anime = State()
    episode_number = State()
    video = State()
    public_post = State()


class DeleteAnime(StatesGroup):
    choose_anime = State()


class Broadcast(StatesGroup):
    content = State()
    confirm = State()


class AddChannel(StatesGroup):
    chat_id = State()
    title = State()
    link = State()


class GrantVip(StatesGroup):
    user_id = State()
    days = State()


class RemoveVip(StatesGroup):
    user_id = State()


class EditProfile(StatesGroup):
    display_name = State()
