import os
import datetime
from airunner.aihandler.models.agent_models import Base, Conversation, Message, Summary
from airunner.aihandler.models.database_handler import DatabaseHandler


class AgentDBHandler(DatabaseHandler):
    def load_history_from_db(self, conversation_id):
        with self.get_db_session() as session:
            messages = session.query(Message).filter_by(conversation_id=conversation_id).order_by(Message.timestamp).all()
            return [
                {
                    "role": message.role,
                    "content": message.content,
                    "name": message.name,
                    "is_bot": message.is_bot,
                    "timestamp": message.timestamp,
                    "conversation_id": message.conversation_id
                } for message in messages
            ]

    def add_message_to_history(self, content, role, name, is_bot, conversation_id):
        timestamp = datetime.datetime.now()  # Ensure timestamp is a datetime object
        with self.get_db_session() as session:
            message = Message(
                role=role,
                content=content,
                name=name,
                is_bot=is_bot,
                timestamp=timestamp,
                conversation_id=conversation_id
            )
            session.add(message)
            session.commit()

    def create_conversation(self):
        with self.get_db_session() as session:
            conversation = Conversation(
                timestamp=datetime.datetime.utcnow(),
                title=""
            )
            session.add(conversation)
            session.commit()
            return conversation.id

    def update_conversation_title(self, conversation_id, title):
        with self.get_db_session() as session:
            conversation = session.query(Conversation).filter_by(id=conversation_id).first()
            if conversation:
                conversation.title = title
                session.commit()

    def add_summary(self, content, conversation_id):
        timestamp = datetime.datetime.now()  # Ensure timestamp is a datetime object
        with self.get_db_session() as session:
            summary = Summary(
                content=content,
                timestamp=timestamp,
                conversation_id=conversation_id
            )
            session.add(summary)
            session.commit()

    def create_conversation_with_messages(self, messages):
        conversation_id = self.create_conversation()
        for message in messages:
            self.add_message_to_history(
                content=message["content"],
                role=message["role"],
                name=message["name"],
                is_bot=message["is_bot"],
                conversation_id=conversation_id
            )
        return conversation_id

    def get_all_conversations(self):
        session = self.Session()
        conversations = session.query(Conversation).all()
        session.close()
        return conversations

    def delete_conversation(self, conversation_id):
        session = self.Session()
        try:
            session.query(Message).filter_by(conversation_id=conversation_id).delete()
            session.query(Summary).filter_by(conversation_id=conversation_id).delete()
            session.query(Conversation).filter_by(id=conversation_id).delete()
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error deleting conversation: {e}")
        finally:
            session.close()

    def get_most_recent_conversation_id(self):
        session = self.Session()
        conversation = session.query(Conversation).order_by(Conversation.timestamp.desc()).first()
        session.close()
        return conversation.id if conversation else None
