import json
import re
import datetime
import telebot
import vk_api
from telebot import types

# Load credentials from credentials.json
def load_credentials():
    with open('credentials.json', 'r') as file:
        return json.load(file)

# VK authorization function
def vk_authorization(login, password, app_id):
    vk_session = vk_api.VkApi(login=login, password=password, app_id=app_id)
    try:
        vk_session.auth()
    except vk_api.AuthError as e:
        print("VK Authorization failed:", e)
        raise
    return vk_session.get_api()

# Get posts by group ID function
def get_posts(vk, group_id, count=20):
    try:
        return vk.wall.get(owner_id=group_id * -1, count=count)
    except vk_api.VkApiError as e:
        print("Error fetching posts:", e)
        raise

# Extract events from VK posts
def extract_events_from_posts(vk, vk_posts):
    post_text_list = [item['text'] for item in vk_posts['items']]
    group_ids = re.findall(r"\[club(\d+)\|", str(post_text_list))
    uniq_group_ids = list(set(group_ids))
    try:
        group_list = vk.groups.getById(group_ids=uniq_group_ids, fields=['id', 'name', 'screen_name', 'type', 'photo_200', 'description', 'place', 'public_date_label', 'start_date'])
    except vk_api.VkApiError as e:
        print("Error fetching group info:", e)
        raise
    return [group for group in group_list if group['type'] == 'event']

# Event class
class Event:
    def __init__(self, event_id, name, screen_name, url, description, date, image_url=None):
        self.event_id = event_id
        self.name = name
        self.screen_name = screen_name
        self.url = url
        self.description = description
        self.date = date
        self.image_url = image_url
    
    def display_info(self):
        print("Event ID:", self.event_id)
        print("Event Name:", self.name)
        print("Event Screen Name:", self.screen_name)
        print("Event URL:", self.url)
        print("Event Description:", self.description)
        print("Event Date:", self.date)
        print("Event Image URL:", self.image_url)

# Filter events for a given week
def filter_events_for_week(events, week_start, week_end):
    return [event for event in events if week_start <= event.date <= week_end]

# Initialize Telegram bot
def initialize_telegram_bot(token):
    return telebot.TeleBot(token)

# Main function
def main():
    credentials = load_credentials()
    token = credentials["telegram_credentials"]["token"]
    vk_creds = credentials["vk_credentials"]
    
    bot = initialize_telegram_bot(token)
    vk = vk_authorization(vk_creds["login"], vk_creds["password"], vk_creds["app_id"])
    
    try:
        vk_post_list = get_posts(vk, 87677042)
        vk_event_list = extract_events_from_posts(vk, vk_post_list)
    except Exception as e:
        bot.send_message("An error occurred while fetching events. Please try again later.")
        print("Error:", e)
        return

    parsed_event_list = []
    for event in vk_event_list:
        parsed_event = Event(
            event_id=event['id'],
            name=event['name'],
            screen_name=event['screen_name'],
            url=f"https://vk.com/{event['screen_name']}",
            description=event['description'],
            date=datetime.datetime.fromtimestamp(event['start_date']).strftime('%Y-%m-%d'),
            image_url=event['photo_200']
        )
        parsed_event_list.append(parsed_event)

    now = datetime.datetime.now()
    monday = (now - datetime.timedelta(days=now.weekday()))
    sunday = monday + datetime.timedelta(days=6)

    week_event_list = filter_events_for_week(parsed_event_list, monday.strftime('%Y-%m-%d'), sunday.strftime('%Y-%m-%d'))

    # Command handlers
    @bot.message_handler(commands=['start'])
    def start(message):
        markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        itembtn1 = types.KeyboardButton('/events')
        markup.add(itembtn1)
        bot.send_message(message.chat.id, "Hello! I am your bot. Press /events to see events.", reply_markup=markup)
    
    @bot.message_handler(commands=['events'])
    def events_command(message):
        all_events = ""
        for event in week_event_list:
            all_events += f"{event.date} {event.name}\nСсылка на движ: {event.url}\n\n"
        bot.send_message(message.chat.id, all_events)
    
    @bot.message_handler(func=lambda message: True)
    def unknown(message):
        bot.reply_to(message, "Sorry, I didn't understand that command.")
    
    bot.polling()

if __name__ == "__main__":
    main()
