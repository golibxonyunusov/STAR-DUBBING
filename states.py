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


class DeleteAnime(StatesGroup):
    choose_anime = State()


class Broadcast(StatesGroup):
    content = State()
    confirm = State()


class AddChannel(StatesGroup):
    chat_id = State()
    title = State()
    link = State()
