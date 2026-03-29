from django.db import models
from accounts.models import User
from items.models import Item


class Conversation(models.Model):
    """Conversation thread between two users about a specific item"""
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='conversations', null=True, blank=True)
    participant1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_p1')
    participant2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_p2')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Conversation about {self.item.title} between {self.participant1.username} and {self.participant2.username}"
    
    def get_other_participant(self, user):
        """Get the other participant in the conversation"""
        if user == self.participant1:
            return self.participant2
        return self.participant1
    
    class Meta:
        db_table = 'conversations'
        ordering = ['-updated_at']
        unique_together = ['item', 'participant1', 'participant2']


class Message(models.Model):
    """Individual messages in a conversation"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages_sent')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Message from {self.sender.username} at {self.created_at}"
    
    class Meta:
        db_table = 'messages'
        ordering = ['created_at']
