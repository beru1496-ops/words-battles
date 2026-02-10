import pygame
import json
import random
import sys
import os
import math
from sound_manager import SoundManager

# --- Configuration & Constants ---
SCREEN_WIDTH = 1280  # Landscape
SCREEN_HEIGHT = 720
FPS = 60

# Layout Constants
SIDEBAR_WIDTH = 180
MAIN_AREA_WIDTH = SCREEN_WIDTH - SIDEBAR_WIDTH

# Colors
COLOR_BG = (30, 30, 35)
COLOR_SIDEBAR_BG = (25, 25, 30)
COLOR_TEXT_MAIN = (255, 255, 255)
COLOR_TEXT_ACCENT = (255, 215, 0) # Gold
COLOR_HP_BAR = (220, 50, 50)
COLOR_HP_BG = (80, 0, 0)
COLOR_CARD_BG = (240, 240, 240)
COLOR_CARD_BORDER = (100, 100, 100)
COLOR_TIMER_BAR = (50, 200, 50)
COLOR_BUTTON = (50, 50, 70)
COLOR_BUTTON_HOVER = (70, 70, 90)
COLOR_CORRECT = (50, 200, 50)
COLOR_WRONG = (200, 50, 50)
COLOR_RESULT_BG = (40, 40, 50)

# Fonts
FONT_NAME_JAPANESE = "Meiryo"  # Windows default
FONT_NAME_ENGLISH = "Arial"

# Game Settings
TURN_TIME = 15
HAND_SIZE = 5
ACTIVE_DECK_SIZE = 10
MASTERY_THRESHOLD = 3
PLAYER_MAX_HP = 100

# --- Resource Loading ---
def load_words(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {path} not found.")
        sys.exit(1)

# --- Classes ---

class Card:
    def __init__(self, data, font_manager):
        self.id = data['id']
        self.word = data['word']
        self.meaning = data['meaning']
        self.level = data['level']
        self.part_of_speech = data['part_of_speech']
        self.mastery = data.get('mastery', 0)
        self.font_manager = font_manager
        
        self.mode = data.get('mode', 'select').upper()  # SELECTION or TYPING
        if self.mode == 'SELECT':
            self.mode = 'SELECTION'
        self.rect = pygame.Rect(0, 0, 90, 120) 
        self.selected = False
        self.is_correct = None 
        self.typed_text = ""
    
    def get_display_text(self):
        if self.mode == "SELECTION":
            return self.word
        elif self.mode == "TYPING":
            if len(self.typed_text) == 0:
                 return f"{self.word[0]} " + "_ " * (len(self.word) - 1)
            else:
                 return self.typed_text + " " + "_ " * (len(self.word) - len(self.typed_text))

    def draw_thumbnail(self, surface, x, y, width, height, is_active):
        self.rect = pygame.Rect(x, y, width, height)
        
        color = (255, 255, 255) if is_active else (180, 180, 180)
        if self.is_correct is True: color = (150, 255, 150)
        elif self.is_correct is False: color = (255, 150, 150)
        
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        
        border_width = 3 if is_active else 1
        border_color = (255, 215, 0) if is_active else COLOR_CARD_BORDER
        pygame.draw.rect(surface, border_color, self.rect, width=border_width, border_radius=8)
        
        font = self.font_manager.get_font(20, 'english')
        text_surf = font.render(self.word, True, (0,0,0))
        text_rect = text_surf.get_rect(center=(x + width/2, y + height/2))
        surface.blit(text_surf, text_rect)
        
        # Show mode indicator
        mode_font = self.font_manager.get_font(12, 'english')
        mode_text = "S" if self.mode == "SELECTION" else "T"
        mode_color = (50, 150, 50) if self.mode == "SELECTION" else (150, 50, 150)
        mode_surf = mode_font.render(mode_text, True, mode_color)
        surface.blit(mode_surf, (x + 5, y + 5))


class Player:
    """Manages player stats for RPG mechanics."""
    def __init__(self, permanent_stats=None):
        if permanent_stats is None:
            permanent_stats = {}
            
        self.max_hp = PLAYER_MAX_HP + permanent_stats.get("hp", 0)
        self.current_hp = self.max_hp
        self.defense = permanent_stats.get("defense", 0)
        self.attack_multiplier = 1.0 + permanent_stats.get("attack", 0.0)
        self.time_bonus = 0  # Extra seconds on timer
    
    def take_damage(self, amount):
        """Apply damage with defense reduction (minimum 1 damage)."""
        actual_damage = max(1, amount - self.defense)
        self.current_hp -= actual_damage
        if self.current_hp < 0:
            self.current_hp = 0
        return actual_damage
    
    def heal(self, amount):
        """Heal up to max HP."""
        self.current_hp = min(self.current_hp + amount, self.max_hp)
    
    def apply_bonus(self, bonus_type):
        """Apply a bonus effect."""
        if bonus_type == "iron_wall":
            self.defense += 3
        elif bonus_type == "vitality":
            self.max_hp += 20
            self.heal(20)
        elif bonus_type == "scholar":
            self.time_bonus += 2
        elif bonus_type == "sharp_pen":
            self.attack_multiplier += 0.2
    
    def get_effective_turn_time(self):
        """Get turn time with bonus applied."""
        return TURN_TIME + self.time_bonus


class Enemy:
    def __init__(self, stage=1):
        self.stage = stage
        self.max_hp = 100 + (stage - 1) * 30  # HP increases per stage
        self.hp = self.max_hp
        self.rect = pygame.Rect(0, 0, 120, 120)
    
    def take_damage(self, amount, is_critical=False):
        self.hp -= amount
        if self.hp < 0: self.hp = 0
        return self.hp <= 0

    def draw(self, surface, font_manager):
        pygame.draw.rect(surface, (200, 50, 50), self.rect, border_radius=10)
        pygame.draw.circle(surface, (0,0,0), (self.rect.x + 40, self.rect.y + 40), 10)
        pygame.draw.circle(surface, (0,0,0), (self.rect.x + 80, self.rect.y + 40), 10)
        pygame.draw.line(surface, (0,0,0), (self.rect.x + 40, self.rect.y + 90), (self.rect.x + 80, self.rect.y + 80), 5)

        bar_width = 300
        bar_height = 20
        bar_x = self.rect.centerx - bar_width // 2
        bar_y = self.rect.bottom + 20
        
        pygame.draw.rect(surface, COLOR_HP_BG, (bar_x, bar_y, bar_width, bar_height), border_radius=5)
        hp_pct = self.hp / self.max_hp
        pygame.draw.rect(surface, COLOR_HP_BAR, (bar_x, bar_y, bar_width * hp_pct, bar_height), border_radius=5)
        
        font = font_manager.get_font(16, 'english')
        text = font.render(f"HP: {self.hp}/{self.max_hp}", True, COLOR_TEXT_MAIN)
        surface.blit(text, (bar_x, bar_y - 20))
        
        # Stage indicator
        stage_font = font_manager.get_font(20, 'english')
        stage_text = stage_font.render(f"Stage {self.stage}", True, COLOR_TEXT_ACCENT)
        surface.blit(stage_text, (bar_x + bar_width - 80, bar_y - 20))



class SaveManager:
    """Handles save/load of persistent data (Rank Points, Mastery)."""
    def __init__(self, file_path="save_data.json"):
        self.file_path = file_path
        self.data = self.load_data()
        
    def load_data(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    return json.load(f)
            except:
                return self._default_data()
        else:
            return self._default_data()
    
    def _default_data(self):
        return {
            "rank_points": 0,
            "word_mastery": {},  # "word_id": count
            "upgrades": {
                "hp": 0,
                "attack": 0,
                "defense": 0
            },
            "volume": {
                "bgm": 0.3,
                "se": 0.6,
                "voice": 0.8
            }
        }
        
    def save_data(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.data, f, indent=4)
            
    def get_word_mastery(self, word_id):
        return self.data["word_mastery"].get(str(word_id), 0)
        
    def update_word_mastery(self, word_id):
        str_id = str(word_id)
        self.data["word_mastery"][str_id] = self.data["word_mastery"].get(str_id, 0) + 1
        self.save_data()
        
    def add_rank_points(self, amount):
        self.data["rank_points"] += amount
        self.save_data()
        
    def get_rank_points(self):
        return self.data["rank_points"]
        
    def get_upgrade_level(self, upgrade_type):
        return self.data["upgrades"].get(upgrade_type, 0)
        
    def purchase_upgrade(self, upgrade_type, cost):
        if self.data["rank_points"] >= cost:
            self.data["rank_points"] -= cost
            self.data["upgrades"][upgrade_type] = self.data["upgrades"].get(upgrade_type, 0) + 1
            self.save_data()
            return True
        return False
        
    def get_permanent_stats(self):
        """Calculate bonuses from upgrades."""
        upgrades = self.data["upgrades"]
        return {
            "hp": upgrades.get("hp", 0) * 10,
            "attack": upgrades.get("attack", 0) * 0.1,
            "defense": upgrades.get("defense", 0) * 1
        }
    
    def reset_data(self):
        """Reset all save data to defaults."""
        self.data = self._default_data()
        self.save_data()
        print("Progress reset!")
    
    def get_volume(self, channel):
        """Get volume for channel (bgm/se/voice). Returns 0.0-1.0."""
        if "volume" not in self.data:
            self.data["volume"] = {"bgm": 0.3, "se": 0.6, "voice": 0.8}
        return self.data["volume"].get(channel, 0.5)
    
    def set_volume(self, channel, value):
        """Set volume for channel (bgm/se/voice). Value 0.0-1.0."""
        if "volume" not in self.data:
            self.data["volume"] = {"bgm": 0.3, "se": 0.6, "voice": 0.8}
        self.data["volume"][channel] = max(0.0, min(1.0, value))
        self.save_data()


class DeckManager:
    """Manages Active Deck and Card Pool, filtering mastered words."""
    def __init__(self, all_words, font_manager, save_manager):
        self.all_words = all_words
        self.font_manager = font_manager
        self.save_manager = save_manager
        
        # Filter words based on mastery (Hall of Fame check)
        # Words with > 10 correct answers are considered "Hall of Fame" and skipped if possible
        active_candidates = []
        hall_of_fame = []
        
        for w in all_words:
            mastery_count = self.save_manager.get_word_mastery(w['id'])
            if mastery_count > 10:
                hall_of_fame.append(w)
            else:
                active_candidates.append(w)
        
        # If we don't have enough active candidates, fill with hall of fame words
        min_cards = ACTIVE_DECK_SIZE + HAND_SIZE
        if len(active_candidates) < min_cards:
            needed = min_cards - len(active_candidates)
            if hall_of_fame:
                active_candidates.extend(random.sample(hall_of_fame, min(needed, len(hall_of_fame))))
        
        # All cards from available candidates
        all_cards = [Card(w, font_manager) for w in active_candidates]
        random.shuffle(all_cards)
        
        # Active Deck: Up to 10 cards in current rotation
        self.active_deck = all_cards[:ACTIVE_DECK_SIZE]
        # Card Pool: Remaining cards waiting to be used
        self.card_pool = all_cards[ACTIVE_DECK_SIZE:]
        # Mastered Pool: Cards that have been mastered (mode changed to TYPING)
        self.mastered_pool = []
        
        # Hand: Cards currently visible in battle (drawn from active_deck)
        self.hand = []
        # Discard: Cards used in current battle, will be shuffled back into active_deck
        self.discard = []
        
    def draw_hand(self, count=HAND_SIZE):
        """Draw cards from active_deck to hand."""
        while len(self.hand) < count:
            available = [c for c in self.active_deck if c not in self.hand and c not in self.discard]
            if not available:
                # Shuffle discard back into active rotation
                if self.discard:
                    for c in self.discard:
                        c.is_correct = None  # Reset visual state
                    self.discard = []
                    available = [c for c in self.active_deck if c not in self.hand]
                if not available:
                    break
            
            card = random.choice(available)
            self.hand.append(card)
            
    def return_hand_to_discard(self):
        """Move all hand cards to discard pile."""
        self.discard.extend(self.hand)
        self.hand = []
    
    def reload_hand(self):
        """Reload hand after a round."""
        self.return_hand_to_discard()
        self.draw_hand(HAND_SIZE)
        
    def process_mastery(self):
        """Check cards for mastery threshold and handle graduation.
        Returns: (mastered_cards, new_cards)
        """
        mastered = []
        new_cards = []
        
        # Find mastered cards in active deck
        for card in self.active_deck[:]:
            if card.mastery >= MASTERY_THRESHOLD:
                mastered.append(card)
                self.active_deck.remove(card)
                # Change mode to TYPING and move to mastered pool
                card.mode = "TYPING"
                card.mastery = 0  # Reset for typing mode
                self.mastered_pool.append(card)
        
        # Refill active deck from pool
        while len(self.active_deck) < ACTIVE_DECK_SIZE and self.card_pool:
            new_card = self.card_pool.pop(0)
            self.active_deck.append(new_card)
            new_cards.append(new_card)
        
        # If pool is empty, pull from mastered pool (typing mode cards)
        while len(self.active_deck) < ACTIVE_DECK_SIZE and self.mastered_pool:
            recycled = self.mastered_pool.pop(0)
            self.active_deck.append(recycled)
            new_cards.append(recycled)
        
        return mastered, new_cards


class FontManager:
    def __init__(self):
        self.fonts = {}
        
    def get_font(self, size, type='english'):
        key = (size, type)
        if key not in self.fonts:
            name = FONT_NAME_JAPANESE if type == 'japanese' else FONT_NAME_ENGLISH
            self.fonts[key] = pygame.font.SysFont(name, size)
        return self.fonts[key]

class InputBox:
    def __init__(self, x, y, w, h, font):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = COLOR_BUTTON
        self.text = ""
        self.font = font
        self.active = True

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                return self.text
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                self.text += event.unicode
        return None

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect, border_radius=5)
        pygame.draw.rect(screen, COLOR_TEXT_ACCENT, self.rect, 2, border_radius=5)
        txt_surface = self.font.render(self.text, True, COLOR_TEXT_MAIN)
        screen.blit(txt_surface, (self.rect.x + 10, self.rect.y + 10))

class Button:
    def __init__(self, rect, text, font, callback, value=None):
        self.rect = rect
        self.text = text
        self.font = font
        self.callback = callback
        self.value = value
        self.hovered = False
        
    def draw(self, screen):
        color = COLOR_BUTTON_HOVER if self.hovered else COLOR_BUTTON
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        pygame.draw.rect(screen, (100,100,100), self.rect, 2, border_radius=8)
        
        txt_surf = self.font.render(self.text, True, COLOR_TEXT_MAIN)
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        screen.blit(txt_surf, txt_rect)
        
    def check_input(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hovered:
                if self.callback:
                    return self.callback(self.value)
        return None


class ResultScreen:
    """Displays battle results and handles transition to next stage."""
    def __init__(self, font_manager, sound_manager, mastered_cards, new_cards, stage, on_next_stage):
        self.font_manager = font_manager
        self.sound_manager = sound_manager
        self.mastered_cards = mastered_cards
        self.new_cards = new_cards
        self.stage = stage
        self.on_next_stage = on_next_stage
        
        # Next Stage button
        btn_rect = pygame.Rect(0, 0, 250, 60)
        btn_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 80)
        self.next_button = Button(btn_rect, "Next Stage →", font_manager.get_font(28, 'english'), self._handle_next, None)
    
    def _handle_next(self, value):
        self.on_next_stage()
        return True
    
    def handle_event(self, event):
        return self.next_button.check_input(event)
    
    def draw(self, screen):
        screen.fill(COLOR_RESULT_BG)
        
        center_x = SCREEN_WIDTH // 2
        
        # Title
        title_font = self.font_manager.get_font(48, 'english')
        title_surf = title_font.render(f"Stage {self.stage} Complete!", True, COLOR_TEXT_ACCENT)
        title_rect = title_surf.get_rect(center=(center_x, 60))
        screen.blit(title_surf, title_rect)
        
        # Mastered Section
        section_font = self.font_manager.get_font(28, 'english')
        item_font = self.font_manager.get_font(22, 'japanese')
        
        y_offset = 130
        
        mastered_title = section_font.render("🎓 Mastered Words (Graduated to Typing Mode)", True, (100, 255, 100))
        screen.blit(mastered_title, (80, y_offset))
        y_offset += 40
        
        if self.mastered_cards:
            for card in self.mastered_cards:
                text = f"• {card.word} - {card.meaning}"
                surf = item_font.render(text, True, COLOR_TEXT_MAIN)
                screen.blit(surf, (100, y_offset))
                y_offset += 30
        else:
            none_surf = item_font.render("(None this round)", True, (150, 150, 150))
            screen.blit(none_surf, (100, y_offset))
            y_offset += 30
        
        y_offset += 30
        
        # New Cards Section
        new_title = section_font.render("✨ New Words Added to Active Deck", True, (100, 200, 255))
        screen.blit(new_title, (80, y_offset))
        y_offset += 40
        
        if self.new_cards:
            for card in self.new_cards:
                mode_str = "(Typing)" if card.mode == "TYPING" else "(Select)"
                text = f"• {card.word} - {card.meaning} {mode_str}"
                surf = item_font.render(text, True, COLOR_TEXT_MAIN)
                screen.blit(surf, (100, y_offset))
                y_offset += 30
        else:
            none_surf = item_font.render("(None - deck is full)", True, (150, 150, 150))
            screen.blit(none_surf, (100, y_offset))
        
        # Draw button
        self.next_button.draw(screen)


class GameOverScreen:
    """Displays game over screen with restart option."""
    def __init__(self, font_manager, sound_manager, stage, on_restart):
        self.font_manager = font_manager
        self.sound_manager = sound_manager
        self.stage = stage
        self.on_restart = on_restart
        
        # Return to Title button
        btn_rect = pygame.Rect(0, 0, 250, 60)
        btn_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 120)
        self.restart_button = Button(btn_rect, "Return to Title", font_manager.get_font(28, 'english'), self._handle_restart, None)
    
    def _handle_restart(self, value):
        self.on_restart()
        return True
    
    def handle_event(self, event):
        return self.restart_button.check_input(event)
    
    def draw(self, screen):
        screen.fill((40, 20, 20))
        
        center_x = SCREEN_WIDTH // 2
        
        # Game Over text
        title_font = self.font_manager.get_font(72, 'english')
        title_surf = title_font.render("GAME OVER", True, (200, 50, 50))
        title_rect = title_surf.get_rect(center=(center_x, 150))
        screen.blit(title_surf, title_rect)
        
        # Stage reached
        stage_font = self.font_manager.get_font(36, 'english')
        stage_surf = stage_font.render(f"You reached Stage {self.stage}", True, COLOR_TEXT_MAIN)
        stage_rect = stage_surf.get_rect(center=(center_x, 250))
        screen.blit(stage_surf, stage_rect)
        
        # Encouragement
        msg_font = self.font_manager.get_font(24, 'japanese')
        msg_surf = msg_font.render("もう一度挑戦しよう！", True, (200, 200, 200))
        msg_rect = msg_surf.get_rect(center=(center_x, 320))
        screen.blit(msg_surf, msg_rect)
        
        # Draw button
        self.restart_button.draw(screen)


# Bonus definitions
BONUS_LIST = [
    {"id": "iron_wall", "name": "Iron Wall", "desc": "Defense +3", "icon": "🛡️"},
    {"id": "vitality", "name": "Vitality", "desc": "Max HP +20 & Heal 20", "icon": "❤️"},
    {"id": "scholar", "name": "Scholar", "desc": "Time Limit +2s", "icon": "📚"},
    {"id": "sharp_pen", "name": "Sharp Pen", "desc": "Attack +0.2x", "icon": "✏️"},
]


class BonusSelectScreen:
    """Roguelike bonus selection screen after every 3 stages."""
    def __init__(self, font_manager, sound_manager, player, on_select_done):
        self.font_manager = font_manager
        self.sound_manager = sound_manager
        self.player = player
        self.on_select_done = on_select_done
        
        # Select 3 random bonuses
        self.bonuses = random.sample(BONUS_LIST, 3)
        self.buttons = []
        
        btn_w, btn_h = 300, 150
        center_x = SCREEN_WIDTH // 2
        start_x = center_x - (btn_w * 1.5) - 30
        y = 350
        
        for i, bonus in enumerate(self.bonuses):
            x = start_x + i * (btn_w + 30)
            rect = pygame.Rect(x, y, btn_w, btn_h)
            self.buttons.append({
                "rect": rect,
                "bonus": bonus,
                "hovered": False
            })
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self.buttons:
                if btn["rect"].collidepoint(event.pos):
                    self.player.apply_bonus(btn["bonus"]["id"])
                    self.on_select_done()
                    return True
        elif event.type == pygame.MOUSEMOTION:
            for btn in self.buttons:
                btn["hovered"] = btn["rect"].collidepoint(event.pos)
        return False
    
    def draw(self, screen):
        screen.fill(COLOR_BG)
        
        center_x = SCREEN_WIDTH // 2
        
        # Title
        title_font = self.font_manager.get_font(48, 'english')
        title_surf = title_font.render("Choose Your Bonus!", True, COLOR_TEXT_ACCENT)
        title_rect = title_surf.get_rect(center=(center_x, 150))
        screen.blit(title_surf, title_rect)
        
        # Subtitle
        sub_font = self.font_manager.get_font(24, 'japanese')
        sub_surf = sub_font.render("パワーアップを選んでください", True, (200, 200, 200))
        sub_rect = sub_surf.get_rect(center=(center_x, 220))
        screen.blit(sub_surf, sub_rect)
        
        # Draw bonus cards
        for btn in self.buttons:
            rect = btn["rect"]
            bonus = btn["bonus"]
            
            # Card background
            color = COLOR_BUTTON_HOVER if btn["hovered"] else COLOR_BUTTON
            pygame.draw.rect(screen, color, rect, border_radius=15)
            pygame.draw.rect(screen, COLOR_TEXT_ACCENT if btn["hovered"] else (100, 100, 100), rect, width=3, border_radius=15)
            
            # Icon (text emoji)
            icon_font = self.font_manager.get_font(40, 'japanese')
            icon_surf = icon_font.render(bonus["icon"], True, COLOR_TEXT_MAIN)
            icon_rect = icon_surf.get_rect(center=(rect.centerx, rect.y + 40))
            screen.blit(icon_surf, icon_rect)
            
            # Name
            name_font = self.font_manager.get_font(24, 'english')
            name_surf = name_font.render(bonus["name"], True, COLOR_TEXT_MAIN)
            name_rect = name_surf.get_rect(center=(rect.centerx, rect.y + 85))
            screen.blit(name_surf, name_rect)
            
            # Description
            desc_font = self.font_manager.get_font(18, 'english')
            desc_surf = desc_font.render(bonus["desc"], True, (180, 180, 180))
            desc_rect = desc_surf.get_rect(center=(rect.centerx, rect.y + 120))
            screen.blit(desc_surf, desc_rect)


class Battle:
    """Handles a single battle session."""
    def __init__(self, deck_manager, font_manager, stage, player, save_manager, sound_manager, on_battle_end, on_game_over):
        self.deck_manager = deck_manager
        self.font_manager = font_manager
        self.stage = stage
        self.on_battle_end = on_battle_end
        self.on_game_over = on_game_over
        self.save_manager = save_manager
        self.sound_manager = sound_manager
        
        # Player object (persistent across stages)
        self.player = player
        
        self.main_area_center_x = MAIN_AREA_WIDTH // 2
        
        self.enemy = Enemy(stage)
        self.enemy.rect.centerx = self.main_area_center_x
        self.enemy.rect.y = 50
        
        # Timer uses player's time bonus
        self.timer = self.player.get_effective_turn_time()
        self.active_card_index = 0
        self.message = ""
        self.message_timer = 0
        
        self.state = "COUNTDOWN"
        self.countdown_timer = 3.0
        
        # Switch to battle BGM
        self.sound_manager.play_bgm("たったそれだけの物語.wav")
        
        self.buttons = []
        self.input_box = None
        
        # Show answer state
        self.show_answer_timer = 0
        self.correct_answer_text = ""
        
        # Enemy attack state
        self.enemy_attack_timer = 0
        self.enemy_attack_damage = 0
        self.screen_shake_offset = 0
        
        # Prepare hand
        self.deck_manager.hand = []
        self.deck_manager.discard = []
        self.deck_manager.draw_hand(HAND_SIZE)
        self.setup_ui_for_active_card()
    
    def setup_ui_for_active_card(self):
        self.buttons = []
        self.input_box = None
        
        if not self.deck_manager.hand:
            return
            
        if self.active_card_index >= len(self.deck_manager.hand):
            return
            
        card = self.deck_manager.hand[self.active_card_index]
        
        # Play Voice (TTS) only during play (not countdown)
        if self.state == "PLAYING":
             self.sound_manager.play_voice(card.word)
        
        center_x = self.main_area_center_x
        
        if card.mode == "SELECTION":
            correct_meaning = card.meaning
            distractors = [w['meaning'] for w in self.deck_manager.all_words if w['meaning'] != correct_meaning]
            options = random.sample(distractors, min(3, len(distractors))) + [correct_meaning]
            random.shuffle(options)
            
            btn_w, btn_h = 600, 60 
            start_y = 350
            for i, opt in enumerate(options):
                rect = pygame.Rect(0, 0, btn_w, btn_h)
                rect.centerx = center_x
                rect.y = start_y + i*(btn_h+20)
                self.buttons.append(Button(rect, opt, self.font_manager.get_font(24, 'japanese'), self.on_answer, opt))

        elif card.mode == "TYPING":
            box_w, box_h = 400, 60
            self.input_box = InputBox(center_x - box_w//2, 400, box_w, box_h, self.font_manager.get_font(32, 'english'))

    def on_answer(self, value):
        if self.state != "PLAYING": return

        if self.active_card_index >= len(self.deck_manager.hand): return
        
        card = self.deck_manager.hand[self.active_card_index]
        
        is_correct = False
        if card.mode == "SELECTION":
             if value == card.meaning:
                 is_correct = True
        elif card.mode == "TYPING":
             if value.lower().strip() == card.word.lower().strip():
                 is_correct = True
        
        if is_correct:
            self.handle_correct(card)
        else:
            self.handle_wrong(card)
            
    def handle_correct(self, card):
        base_damage = 10
        if card.mode == "TYPING":
            base_damage = 20
        
        # Apply attack multiplier
        damage = int(base_damage * self.player.attack_multiplier)
            
        card.is_correct = True
        card.mastery += 1
        
        # Record mastery to save data
        # Record mastery to save data
        self.save_manager.update_word_mastery(card.id)
        
        # Play SE
        self.sound_manager.play_se("correct.mp3")
        
        self.enemy.take_damage(damage)
        self.message = f"Correct! ({damage} dmg)"
        self.message_timer = 30
        
        self.active_card_index += 1
        
        if self.active_card_index >= len(self.deck_manager.hand):
            crit_damage = int(20 * self.player.attack_multiplier)
            self.enemy.take_damage(crit_damage) 
            
            # Heal player on successful reload
            heal_amount = 10
            self.player.heal(heal_amount)
            self.message = f"RELOAD CRIT! +{heal_amount} HP!"
            self.message_timer = 60
            
            self.deck_manager.reload_hand()
            self.active_card_index = 0
            
        self.setup_ui_for_active_card()

    def handle_wrong(self, card):
        # Pause timer and show correct answer
        self.state = "SHOW_ANSWER"
        self.show_answer_timer = 2.0  # Show for 2 seconds
        card.is_correct = False
        
        # Play SE
        self.sound_manager.play_se("wrong.mp3")
        
        # Prepare correct answer text
        if card.mode == "SELECTION":
            self.correct_answer_text = f"正解: {card.meaning}"
        else:
            self.correct_answer_text = f"正解: {card.word}"
        
        self.message = "Wrong!"
        self.message_timer = 30

    def handle_enemy_turn(self):
        """Called when timer runs out - enemy attacks player."""
        base_damage = 20 + (self.stage * 5)  # Damage increases with stage
        actual_damage = self.player.take_damage(base_damage)
        self.sound_manager.play_se("attack.mp3")
        self.enemy_attack_damage = actual_damage
        
        if self.player.current_hp <= 0:
            self.state = "GAME_OVER"
            self.on_game_over()
        else:
            # Transition to ENEMY_ATTACK state with delay
            self.state = "ENEMY_ATTACK"
            self.enemy_attack_timer = 1.5
            self.screen_shake_offset = 10  # Start shake

    def update(self, dt):
        if self.state == "COUNTDOWN":
            self.countdown_timer -= dt
            if self.countdown_timer <= 0:
                self.state = "PLAYING"
                self.message = "START!"
                self.message_timer = 30
                
                # Play voice for the first card
                if self.deck_manager.hand and self.active_card_index < len(self.deck_manager.hand):
                     card = self.deck_manager.hand[self.active_card_index]
                     self.sound_manager.play_voice(card.word)

        if self.state == "PLAYING":
            self.timer -= dt
            if self.timer <= 0:
                self.handle_enemy_turn()

            if self.message_timer > 0:
                self.message_timer -= 1
                
            if self.enemy.hp <= 0:
                self.state = "WIN"
                self.on_battle_end()
        
        # Handle SHOW_ANSWER state (timer paused)
        if self.state == "SHOW_ANSWER":
            self.show_answer_timer -= dt
            if self.message_timer > 0:
                self.message_timer -= 1
            if self.show_answer_timer <= 0:
                # Resume game, apply penalty, move to next card
                self.timer -= 2
                if self.timer < 0:
                    self.timer = 0
                self.active_card_index += 1
                if self.active_card_index >= len(self.deck_manager.hand):
                    self.deck_manager.reload_hand()
                    self.active_card_index = 0
                self.setup_ui_for_active_card()
                self.state = "PLAYING"
        
        # Handle ENEMY_ATTACK state (damage delay)
        if self.state == "ENEMY_ATTACK":
            self.enemy_attack_timer -= dt
            # Decay screen shake
            self.screen_shake_offset = max(0, self.screen_shake_offset - dt * 15)
            if self.enemy_attack_timer <= 0:
                # Resume: reload hand and continue
                self.timer = self.player.get_effective_turn_time()
                self.deck_manager.reload_hand()
                self.active_card_index = 0
                self.setup_ui_for_active_card()
                self.state = "PLAYING"
                # Play voice for new card
                if self.deck_manager.hand and self.active_card_index < len(self.deck_manager.hand):
                    card = self.deck_manager.hand[self.active_card_index]
                    self.sound_manager.play_voice(card.word)

    def handle_event(self, event):
        if self.state == "PLAYING":
            if self.buttons: 
                for btn in self.buttons:
                     res = btn.check_input(event)
                     if res: break 

            if self.input_box and self.active_card_index < len(self.deck_manager.hand):
                 card = self.deck_manager.hand[self.active_card_index]
                 if card.mode == "TYPING":
                     res = self.input_box.handle_event(event) 
                     if res is not None:
                         self.on_answer(res)
                         self.input_box.text = "" 
                     card.typed_text = self.input_box.text

    def draw(self, screen):
        screen.fill(COLOR_BG)
        
        # Sidebar
        pygame.draw.rect(screen, COLOR_SIDEBAR_BG, (MAIN_AREA_WIDTH, 0, SIDEBAR_WIDTH, SCREEN_HEIGHT))
        
        center_x = self.main_area_center_x
        
        # Enemy
        self.enemy.draw(screen, self.font_manager)
        
        # Timer (uses effective turn time with bonus)
        effective_time = self.player.get_effective_turn_time()
        timer_w = MAIN_AREA_WIDTH * (self.timer / effective_time)
        pygame.draw.rect(screen, COLOR_TIMER_BAR, (0, 0, timer_w, 10))
        
        # Player HP Bar (bottom of main area)
        hp_bar_width = 400
        hp_bar_height = 25
        hp_bar_x = center_x - hp_bar_width // 2
        hp_bar_y = SCREEN_HEIGHT - 50
        
        pygame.draw.rect(screen, COLOR_HP_BG, (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height), border_radius=5)
        hp_pct = max(0, self.player.current_hp / self.player.max_hp)
        hp_color = (50, 200, 50) if hp_pct > 0.3 else (200, 50, 50)
        pygame.draw.rect(screen, hp_color, (hp_bar_x, hp_bar_y, hp_bar_width * hp_pct, hp_bar_height), border_radius=5)
        
        hp_font = self.font_manager.get_font(18, 'english')
        hp_text = hp_font.render(f"Player HP: {self.player.current_hp}/{self.player.max_hp}", True, COLOR_TEXT_MAIN)
        hp_text_rect = hp_text.get_rect(center=(center_x, hp_bar_y + hp_bar_height // 2))
        screen.blit(hp_text, hp_text_rect)
        
        # Question / Active Card
        if self.active_card_index < len(self.deck_manager.hand):
            current_card = self.deck_manager.hand[self.active_card_index]
            
            q_font = self.font_manager.get_font(64, 'english')
            display_text = current_card.get_display_text() 
            q_surf = q_font.render(display_text, True, COLOR_TEXT_MAIN)
            q_rect = q_surf.get_rect(center=(center_x, 300))
            screen.blit(q_surf, q_rect)
            
            if current_card.mode == "SELECTION":
                 for btn in self.buttons:
                    btn.draw(screen)
            elif current_card.mode == "TYPING" and self.input_box:
                 self.input_box.draw(screen)
                 hint_font = self.font_manager.get_font(24, 'japanese')
                 hint_surf = hint_font.render(f"意味: {current_card.meaning}", True, (200, 200, 200))
                 hint_rect = hint_surf.get_rect(center=(center_x, 480))
                 screen.blit(hint_surf, hint_rect)
        
        # Sidebar (Hand)
        card_w, card_h = 90, 120
        gap = 15
        start_y = 50
        sidebar_center_x = MAIN_AREA_WIDTH + SIDEBAR_WIDTH // 2
        
        for i, card in enumerate(self.deck_manager.hand):
            is_active = (i == self.active_card_index)
            card_x = sidebar_center_x - card_w // 2
            card_y = start_y + i * (card_h + gap)
            card.draw_thumbnail(screen, card_x, card_y, card_w, card_h, is_active)

        # Message Overlay
        if self.message_timer > 0:
            m_font = self.font_manager.get_font(36, 'english')
            m_surf = m_font.render(self.message, True, COLOR_TEXT_ACCENT)
            m_rect = m_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            pygame.draw.rect(screen, (0,0,0,180), m_rect.inflate(20,20), border_radius=10)
            screen.blit(m_surf, m_rect)
        
        # Show Answer Overlay (when wrong)
        if self.state == "SHOW_ANSWER":
            # Semi-transparent overlay
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((100, 0, 0, 150))
            screen.blit(overlay, (0, 0))
            
            # "Wrong!" text
            wrong_font = self.font_manager.get_font(60, 'english')
            wrong_surf = wrong_font.render("Wrong!", True, (255, 100, 100))
            wrong_rect = wrong_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 60))
            screen.blit(wrong_surf, wrong_rect)
            
            # Correct answer
            answer_font = self.font_manager.get_font(40, 'japanese')
            answer_surf = answer_font.render(self.correct_answer_text, True, COLOR_TEXT_MAIN)
            answer_rect = answer_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 20))
            screen.blit(answer_surf, answer_rect)
            
            # Countdown hint
            hint_font = self.font_manager.get_font(20, 'english')
            remaining = max(0, self.show_answer_timer)
            hint_surf = hint_font.render(f"Resuming in {remaining:.1f}s... (-2 sec penalty)", True, (200, 200, 200))
            hint_rect = hint_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 80))
            screen.blit(hint_surf, hint_rect)

        # Countdown Overlay
        if self.state == "COUNTDOWN":
            c_font = self.font_manager.get_font(100, 'english')
            count_val = int(self.countdown_timer) + 1
            c_surf = c_font.render(str(count_val), True, (255, 50, 50))
            c_rect = c_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 100))
            screen.blit(overlay, (0,0))
            screen.blit(c_surf, c_rect)
        
        # Enemy Attack Overlay
        if self.state == "ENEMY_ATTACK":
            # Red flash overlay (fades out as timer decreases)
            flash_alpha = int(min(200, 200 * (self.enemy_attack_timer / 1.5)))
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((200, 0, 0, flash_alpha))
            screen.blit(overlay, (0, 0))
            
            # Damage text
            dmg_font = self.font_manager.get_font(72, 'english')
            dmg_text = f"-{self.enemy_attack_damage} HP!"
            dmg_surf = dmg_font.render(dmg_text, True, (255, 80, 80))
            dmg_rect = dmg_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 40))
            
            # Apply screen shake
            shake_x = int(math.sin(pygame.time.get_ticks() * 0.05) * self.screen_shake_offset)
            shake_y = int(math.cos(pygame.time.get_ticks() * 0.07) * self.screen_shake_offset)
            dmg_rect.x += shake_x
            dmg_rect.y += shake_y
            screen.blit(dmg_surf, dmg_rect)
            
            # "Ouch!" text
            ouch_font = self.font_manager.get_font(36, 'english')
            ouch_surf = ouch_font.render("Ouch!", True, (255, 200, 200))
            ouch_rect = ouch_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 40))
            screen.blit(ouch_surf, ouch_rect)


class ShopScreen:
    """Shop screen for permanent upgrades using Rank Points."""
    def __init__(self, font_manager, save_manager, sound_manager, on_back):
        self.font_manager = font_manager
        self.save_manager = save_manager
        self.sound_manager = sound_manager
        self.on_back = on_back
        
        # Upgrade Buttons
        # HP: 300 pts, Attack: 500 pts, Defense: 500 pts
        self.upgrades = [
            {"id": "hp", "name": "HP Up (+10)", "cost": 300, "desc": "Increase base HP by 10"},
            {"id": "attack", "name": "Atk Up (+0.1)", "cost": 500, "desc": "Increase damage multiplier"},
            {"id": "defense", "name": "Def Up (+1)", "cost": 500, "desc": "Reduce incoming damage"},
        ]
        
        self.buttons = []
        btn_w, btn_h = 300, 80
        start_y = 250
        gap = 20
        center_x = SCREEN_WIDTH // 2
        
        for i, upg in enumerate(self.upgrades):
            rect = pygame.Rect(center_x - btn_w//2, start_y + i*(btn_h+gap), btn_w, btn_h)
            btn = Button(rect, "", font_manager.get_font(20, 'english'), self._buy_upgrade, upg)
            self.buttons.append(btn)
            
        self.back_button = Button(pygame.Rect(50, 50, 150, 50), "Back", font_manager.get_font(24, 'english'), self.on_back, None)

    def _buy_upgrade(self, upgrade_data):
        if self.save_manager.purchase_upgrade(upgrade_data["id"], upgrade_data["cost"]):
            print(f"Purchased {upgrade_data['name']}!")
            return True
        else:
            print("Not enough points!")
            return False

    def handle_event(self, event):
        if self.back_button.check_input(event):
            return
            
        for btn in self.buttons:
            if btn.check_input(event):
                break

    def draw(self, screen):
        screen.fill(COLOR_BG)
        self.back_button.draw(screen)
        
        center_x = SCREEN_WIDTH // 2
        
        # Title
        title_font = self.font_manager.get_font(48, 'english')
        title_surf = title_font.render("Item Shop", True, COLOR_TEXT_ACCENT)
        title_rect = title_surf.get_rect(center=(center_x, 100))
        screen.blit(title_surf, title_rect)
        
        # Points Display
        pts_font = self.font_manager.get_font(32, 'english')
        pts = self.save_manager.get_rank_points()
        pts_surf = pts_font.render(f"Rank Points: {pts}", True, (50, 200, 255))
        pts_rect = pts_surf.get_rect(center=(center_x, 160))
        screen.blit(pts_surf, pts_rect)
        
        # Draw Upgrades
        for i, btn in enumerate(self.buttons):
            upg = self.upgrades[i]
            level = self.save_manager.get_upgrade_level(upg["id"])
            
            # Button Logic (Change color if affordable)
            can_afford = pts >= upg["cost"]
            btn.base_color = COLOR_BUTTON if can_afford else (50, 50, 50)
            btn.hover_color = COLOR_BUTTON_HOVER if can_afford else (60, 60, 60)
            btn.draw(screen)
            
            # Text on button
            font = self.font_manager.get_font(24, 'english')
            text = f"{upg['name']} - {upg['cost']}pts (Lv.{level})"
            text_surf = font.render(text, True, COLOR_TEXT_MAIN if can_afford else (150, 150, 150))
            text_rect = text_surf.get_rect(center=btn.rect.center)
            screen.blit(text_surf, text_rect)


class TitleScreen:
    def __init__(self, font_manager, save_manager, sound_manager, on_start, on_word_list, on_shop, on_settings, on_exit):
        self.font_manager = font_manager
        self.save_manager = save_manager
        self.sound_manager = sound_manager
        self.buttons = []
        
        btn_w, btn_h = 360, 50
        center_x = SCREEN_WIDTH // 2
        start_y = 350
        gap = 15
        
        self.buttons.append(Button(pygame.Rect(center_x - btn_w//2, start_y, btn_w, btn_h), "Start Game", font_manager.get_font(24, 'english'), on_start, None))
        self.buttons.append(Button(pygame.Rect(center_x - btn_w//2, start_y + (btn_h+gap), btn_w, btn_h), "Word List", font_manager.get_font(24, 'english'), on_word_list, None))
        self.buttons.append(Button(pygame.Rect(center_x - btn_w//2, start_y + (btn_h+gap)*2, btn_w, btn_h), "Shop", font_manager.get_font(24, 'english'), on_shop, None))
        self.buttons.append(Button(pygame.Rect(center_x - btn_w//2, start_y + (btn_h+gap)*3, btn_w, btn_h), "Settings", font_manager.get_font(24, 'english'), on_settings, None))
        self.buttons.append(Button(pygame.Rect(center_x - btn_w//2, start_y + (btn_h+gap)*4, btn_w, btn_h), "Exit", font_manager.get_font(24, 'english'), on_exit, None))
        
        # Start BGM
        self.sound_manager.play_bgm("Confront_-The_Fate-_Short.mp3")

    def handle_event(self, event):
        for btn in self.buttons:
            if btn.check_input(event):
                break

    def draw(self, screen):
        screen.fill(COLOR_BG)
        
        # Title
        title_font = self.font_manager.get_font(100, 'english')
        title_surf = title_font.render("Words Battles", True, COLOR_TEXT_ACCENT)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, 200))
        screen.blit(title_surf, title_rect)
        
        # Rank Points
        pts = self.save_manager.get_rank_points()
        pts_font = self.font_manager.get_font(24, 'english')
        pts_surf = pts_font.render(f"Rank Points: {pts}", True, (50, 200, 255))
        pts_rect = pts_surf.get_rect(center=(SCREEN_WIDTH // 2, 280))
        screen.blit(pts_surf, pts_rect)
        
        for btn in self.buttons:
            btn.draw(screen)

class WordListScreen:
    def __init__(self, font_manager, save_manager, sound_manager, words_data, on_back):
        self.font_manager = font_manager
        self.save_manager = save_manager
        self.sound_manager = sound_manager
        self.words_data = words_data
        self.back_button = Button(pygame.Rect(50, 50, 150, 50), "Back", font_manager.get_font(24, 'english'), on_back, None)
        
        self.scroll_y = 0
        self.item_height = 80
        self.total_height = len(words_data) * self.item_height + 200  # + padding
        self.max_scroll = max(0, self.total_height - SCREEN_HEIGHT)
        
        # Scrollbar drag state
        self.dragging_scrollbar = False
        self.scrollbar_x = SCREEN_WIDTH - 28
        self.scrollbar_w = 12
        self.scrollbar_track_y = 130
        self.scrollbar_track_h = SCREEN_HEIGHT - 150

    def _get_thumb_rect(self):
        """Calculate thumb position and size."""
        if self.max_scroll <= 0:
            return None
        visible_ratio = SCREEN_HEIGHT / self.total_height
        thumb_h = max(40, int(self.scrollbar_track_h * visible_ratio))
        scroll_ratio = self.scroll_y / self.max_scroll
        thumb_y = self.scrollbar_track_y + int((self.scrollbar_track_h - thumb_h) * scroll_ratio)
        return pygame.Rect(self.scrollbar_x, thumb_y, self.scrollbar_w, thumb_h)

    def handle_event(self, event):
        self.back_button.check_input(event)
        
        if event.type == pygame.MOUSEWHEEL:
            self.scroll_y -= event.y * 40
            self.scroll_y = max(0, min(self.scroll_y, self.max_scroll))
        
        # Scrollbar drag handling
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            thumb_rect = self._get_thumb_rect()
            if thumb_rect and thumb_rect.collidepoint(event.pos):
                self.dragging_scrollbar = True
        
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_scrollbar = False
        
        if event.type == pygame.MOUSEMOTION and self.dragging_scrollbar:
            # Calculate scroll based on mouse Y position
            mouse_y = event.pos[1]
            thumb_rect = self._get_thumb_rect()
            if thumb_rect:
                thumb_h = thumb_rect.height
                usable_track = self.scrollbar_track_h - thumb_h
                if usable_track > 0:
                    relative_y = mouse_y - self.scrollbar_track_y - thumb_h // 2
                    scroll_ratio = max(0, min(1, relative_y / usable_track))
                    self.scroll_y = int(scroll_ratio * self.max_scroll)
        
    def draw(self, screen):
        screen.fill(COLOR_BG)
        
        # Draw List Items
        start_y = 150 - self.scroll_y
        
        for i, word in enumerate(self.words_data):
            y = start_y + i * self.item_height
            
            # Culling - Skip if out of screen
            if y + self.item_height < 0 or y > SCREEN_HEIGHT:
                continue
                
            # Word Text
            font_eng = self.font_manager.get_font(32, 'english')
            font_jp = self.font_manager.get_font(24, 'japanese')
            
            eng_surf = font_eng.render(word['word'], True, COLOR_TEXT_MAIN)
            jp_surf = font_jp.render(f"- {word['meaning']}", True, (200, 200, 200))
            
            screen.blit(eng_surf, (150, y + 20))
            screen.blit(jp_surf, (150 + eng_surf.get_width() + 20, y + 28))
            
            # Mastery Bar
            mastery = self.save_manager.get_word_mastery(word['id'])
            blocks = min(10, mastery)
            is_mastered = mastery >= 10
            
            bar_x = 700
            bar_y = y + 25
            block_w = 20
            block_h = 30
            gap = 4
            
            for b in range(10):
                bx = bar_x + b * (block_w + gap)
                color = (50, 50, 50) # Empty
                border_color = (100, 100, 100)
                
                if b < blocks:
                    if is_mastered:
                        color = (255, 215, 0) # Gold
                        border_color = (255, 255, 200)
                    else:
                        color = (50, 200, 100) # Green
                        border_color = (100, 255, 150)
                
                pygame.draw.rect(screen, color, (bx, bar_y, block_w, block_h))
                pygame.draw.rect(screen, border_color, (bx, bar_y, block_w, block_h), 1)
            
            # Mastered Star
            if is_mastered:
                # Simple star shape or text icon
                star_font = self.font_manager.get_font(30, 'english')
                star_surf = star_font.render("★", True, (255, 255, 0))
                screen.blit(star_surf, (bar_x + 10 * (block_w + gap) + 10, bar_y - 5))

        # Header Overlay (Background for title)
        pygame.draw.rect(screen, COLOR_BG, (0, 0, SCREEN_WIDTH, 120))
        pygame.draw.line(screen, (100, 100, 100), (0, 120), (SCREEN_WIDTH, 120), 2)
        
        # Title
        title_font = self.font_manager.get_font(60, 'english')
        title_surf = title_font.render("Word List", True, COLOR_TEXT_ACCENT)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, 60))
        screen.blit(title_surf, title_rect)

        # Scrollbar (Right side)
        if self.max_scroll > 0:
            # Track
            pygame.draw.rect(screen, (60, 60, 60), (self.scrollbar_x, self.scrollbar_track_y, self.scrollbar_w, self.scrollbar_track_h), border_radius=4)
            
            # Thumb
            thumb_rect = self._get_thumb_rect()
            if thumb_rect:
                thumb_color = (180, 180, 180) if self.dragging_scrollbar else (120, 120, 120)
                pygame.draw.rect(screen, thumb_color, thumb_rect, border_radius=4)

        self.back_button.draw(screen)

class SettingsScreen:
    def __init__(self, font_manager, save_manager, sound_manager, on_back):
        self.font_manager = font_manager
        self.save_manager = save_manager
        self.sound_manager = sound_manager
        self.back_button = Button(pygame.Rect(50, 50, 150, 50), "Back", font_manager.get_font(24, 'english'), on_back, None)
        
        # Reset Progress Button
        center_x = SCREEN_WIDTH // 2
        self.reset_button = Button(
            pygame.Rect(center_x - 150, 580, 300, 60), 
            "Reset Progress", 
            font_manager.get_font(24, 'english'), 
            self._on_reset, 
            None
        )
        self.reset_confirmed = False
        
        # Volume Sliders
        slider_x = center_x - 200
        slider_w = 400
        slider_h = 8
        
        # Load saved volumes and apply to SoundManager
        bgm_vol = save_manager.get_volume("bgm")
        se_vol = save_manager.get_volume("se")
        voice_vol = save_manager.get_volume("voice")
        
        sound_manager.set_volume_bgm(bgm_vol)
        sound_manager.set_volume_se(se_vol)
        sound_manager.set_volume_voice(voice_vol)
        
        self.sliders = [
            {"label": "BGM Volume",   "channel": "bgm",   "x": slider_x, "y": 250, "w": slider_w, "h": slider_h, "value": bgm_vol},
            {"label": "SE Volume",    "channel": "se",    "x": slider_x, "y": 340, "w": slider_w, "h": slider_h, "value": se_vol},
            {"label": "Voice Volume", "channel": "voice", "x": slider_x, "y": 430, "w": slider_w, "h": slider_h, "value": voice_vol},
        ]
        self.dragging_slider = None  # Index of slider being dragged
    
    def _on_reset(self, _):
        if not self.reset_confirmed:
            self.reset_confirmed = True
        else:
            self.save_manager.reset_data()
            self.reset_confirmed = False
    
    def _get_thumb_x(self, slider):
        return slider["x"] + int(slider["value"] * slider["w"])
    
    def _apply_volume(self, slider):
        """Apply volume change to SoundManager and save."""
        ch = slider["channel"]
        val = slider["value"]
        if ch == "bgm":
            self.sound_manager.set_volume_bgm(val)
        elif ch == "se":
            self.sound_manager.set_volume_se(val)
        elif ch == "voice":
            self.sound_manager.set_volume_voice(val)
        self.save_manager.set_volume(ch, val)
    
    def handle_event(self, event):
        self.back_button.check_input(event)
        self.reset_button.check_input(event)
        
        thumb_radius = 14
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, s in enumerate(self.sliders):
                tx = self._get_thumb_x(s)
                # Check if click is on thumb or track
                if abs(my - s["y"]) < 20 and s["x"] - 5 <= mx <= s["x"] + s["w"] + 5:
                    self.dragging_slider = i
                    # Snap to click position
                    ratio = (mx - s["x"]) / s["w"]
                    s["value"] = max(0.0, min(1.0, ratio))
                    self._apply_volume(s)
                    break
        
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_slider = None
        
        if event.type == pygame.MOUSEMOTION and self.dragging_slider is not None:
            mx = event.pos[0]
            s = self.sliders[self.dragging_slider]
            ratio = (mx - s["x"]) / s["w"]
            s["value"] = max(0.0, min(1.0, ratio))
            self._apply_volume(s)
        
    def draw(self, screen):
        screen.fill(COLOR_BG)
        self.back_button.draw(screen)
        
        # Title
        font = self.font_manager.get_font(48, 'english')
        text = font.render("Settings", True, COLOR_TEXT_MAIN)
        screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 150))
        
        # Volume Sliders
        label_font = self.font_manager.get_font(24, 'english')
        value_font = self.font_manager.get_font(20, 'english')
        
        for i, s in enumerate(self.sliders):
            # Label
            label_surf = label_font.render(s["label"], True, COLOR_TEXT_MAIN)
            screen.blit(label_surf, (s["x"], s["y"] - 30))
            
            # Percentage
            pct = int(s["value"] * 100)
            pct_surf = value_font.render(f"{pct}%", True, (200, 200, 200))
            screen.blit(pct_surf, (s["x"] + s["w"] + 15, s["y"] - 8))
            
            # Track background
            track_rect = pygame.Rect(s["x"], s["y"] - s["h"]//2, s["w"], s["h"])
            pygame.draw.rect(screen, (60, 60, 60), track_rect, border_radius=4)
            
            # Filled portion
            fill_w = int(s["value"] * s["w"])
            if fill_w > 0:
                fill_rect = pygame.Rect(s["x"], s["y"] - s["h"]//2, fill_w, s["h"])
                color = (80, 200, 120) if i == 0 else (100, 180, 255) if i == 1 else (255, 180, 80)
                pygame.draw.rect(screen, color, fill_rect, border_radius=4)
            
            # Thumb
            thumb_x = self._get_thumb_x(s)
            is_dragging = (self.dragging_slider == i)
            thumb_color = (255, 255, 255) if is_dragging else (200, 200, 200)
            thumb_radius = 12 if is_dragging else 10
            pygame.draw.circle(screen, thumb_color, (thumb_x, s["y"]), thumb_radius)
            pygame.draw.circle(screen, (100, 100, 100), (thumb_x, s["y"]), thumb_radius, 2)
        
        # Reset Button
        self.reset_button.draw(screen)
        
        # Confirmation text
        if self.reset_confirmed:
            warn_font = self.font_manager.get_font(20, 'english')
            warn_text = warn_font.render("Click again to confirm reset!", True, (255, 100, 100))
            screen.blit(warn_text, (SCREEN_WIDTH // 2 - warn_text.get_width() // 2, 660))


class Game:
    """Main Game Manager - handles game states and transitions."""
    def __init__(self, word_path):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("English Roguelike")
        self.clock = pygame.time.Clock()
        self.font_manager = FontManager()
        
        self.word_path = word_path
        self.words_data = load_words(word_path)
        self._init_game_state()

    def _init_game_state(self):
        """Initialize or reset game state."""
        self.save_manager = SaveManager()
        self.sound_manager = SoundManager()
        
        # Apply saved volume settings
        self.sound_manager.set_volume_bgm(self.save_manager.get_volume("bgm"))
        self.sound_manager.set_volume_se(self.save_manager.get_volume("se"))
        self.sound_manager.set_volume_voice(self.save_manager.get_volume("voice"))
        
        self.deck_manager = DeckManager(self.words_data, self.font_manager, self.save_manager)
        
        self.stage = 1
        # Create Player with permanent stats
        self.player = Player(self.save_manager.get_permanent_stats())
        self.state = "TITLE"  # TITLE, BATTLE, RESULT, GAME_OVER, WORD_LIST, SETTINGS, BONUS_SELECT, SHOP
        
        self.title_screen = TitleScreen(
            self.font_manager, 
            self.save_manager,
            self.sound_manager,
            self._on_start_game, 
            self._on_open_word_list,
            self._on_open_shop,
            self._on_open_settings,
            self._on_exit_game
        )
        self.battle = None
        self.result_screen = None
        self.game_over_screen = None
        self.word_list_screen = None
        self.settings_screen = None
        self.bonus_screen = None
        self.shop_screen = None
        
        # Results from last battle
        self.last_mastered = []
        self.last_new_cards = []

    def _on_start_game(self, _):
        """Start a new game session."""
        # Refresh player with latest permanent stats (including shop upgrades)
        self.stage = 1
        self.player = Player(self.save_manager.get_permanent_stats())
        self._start_battle()

    def _on_open_word_list(self, _):
        self.state = "WORD_LIST"
        self.word_list_screen = WordListScreen(self.font_manager, self.save_manager, self.sound_manager, self.words_data, self._on_back_to_title)

    def _on_open_shop(self, _):
        self.state = "SHOP"
        self.shop_screen = ShopScreen(self.font_manager, self.save_manager, self.sound_manager, self._on_back_to_title)

    def _on_open_settings(self, _):
        self.state = "SETTINGS"
        self.settings_screen = SettingsScreen(self.font_manager, self.save_manager, self.sound_manager, self._on_back_to_title)

    def _on_exit_game(self, _):
        pygame.quit()
        sys.exit()

    def _on_back_to_title(self, _):
        self.state = "TITLE"
        # Update Rank Points display in Title Screen in case upgrades were bought
        self.title_screen = TitleScreen(
            self.font_manager, 
            self.save_manager,
            self.sound_manager,
            self._on_start_game, 
            self._on_open_word_list,
            self._on_open_shop,
            self._on_open_settings,
            self._on_exit_game
        )

    def _start_battle(self):
        """Initialize a new battle."""
        self.state = "BATTLE"
        self.battle = Battle(
            self.deck_manager,
            self.font_manager,
            self.stage,
            self.player,
            self.save_manager,
            self.sound_manager,
            self._on_battle_end,
            self._on_game_over
        )
        self.result_screen = None
        self.game_over_screen = None
        self.bonus_screen = None

    def _on_battle_end(self):
        """Called when battle is won."""
        # Award Rank Points
        # Battle Win: 50 pts
        # Stage Clear: 100 + (Stage * 10) pts
        battle_win_pts = 50
        stage_clear_pts = 100 + (self.stage * 10)
        total_pts = battle_win_pts + stage_clear_pts
        
        self.save_manager.add_rank_points(total_pts)
        print(f"Gained {total_pts} Rank Points! Total: {self.save_manager.get_rank_points()}")
        
        # Process mastery and get results
        mastered, new_cards = self.deck_manager.process_mastery()
        self.last_mastered = mastered
        self.last_new_cards = new_cards
        
        # Transition to result screen
        self.state = "RESULT"
        self.result_screen = ResultScreen(
            self.font_manager,
            self.sound_manager,
            mastered,
            new_cards,
            self.stage,
            self._on_next_stage
        )
        self.battle = None

    def _on_next_stage(self):
        """Called when player clicks Next Stage."""
        self.stage += 1
        
        # Check if bonus should appear (every 2 stages cleared)
        if (self.stage - 1) % 2 == 0 and self.stage > 1:
            self.state = "BONUS_SELECT"
            self.bonus_screen = BonusSelectScreen(
                self.font_manager,
                self.sound_manager,
                self.player,
                self._on_bonus_selected
            )
            self.result_screen = None
        else:
            self._start_battle()

    def _on_bonus_selected(self):
        """Called when player selects a bonus."""
        self._start_battle()

    def _on_game_over(self):
        """Called when player HP reaches 0."""
        self.state = "GAME_OVER"
        self.game_over_screen = GameOverScreen(
            self.font_manager,
            self.sound_manager,
            self.stage,
            self._on_restart
        )
        self.battle = None

    def _on_restart(self):
        """Called when player clicks Restart."""
        # Reset to title state
        self._init_game_state()

    def update(self):
        dt = self.clock.tick(FPS) / 1000.0
        
        # Update SoundManager
        self.sound_manager.update()
        
        if self.state == "BATTLE" and self.battle:
            self.battle.update(dt)

    def draw(self):
        if self.state == "TITLE":
            self.title_screen.draw(self.screen)
        elif self.state == "WORD_LIST":
            self.word_list_screen.draw(self.screen)
        elif self.state == "SETTINGS":
            self.settings_screen.draw(self.screen)
        elif self.state == "SHOP":
            self.shop_screen.draw(self.screen)
        elif self.state == "BATTLE" and self.battle:
            self.battle.draw(self.screen)
        elif self.state == "RESULT" and self.result_screen:
            self.result_screen.draw(self.screen)
        elif self.state == "GAME_OVER" and self.game_over_screen:
            self.game_over_screen.draw(self.screen)
        elif self.state == "BONUS_SELECT" and self.bonus_screen:
            self.bonus_screen.draw(self.screen)
        
        pygame.display.flip()

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                if self.state == "TITLE":
                    self.title_screen.handle_event(event)
                elif self.state == "WORD_LIST":
                    self.word_list_screen.handle_event(event)
                elif self.state == "SETTINGS":
                    self.settings_screen.handle_event(event)
                elif self.state == "SHOP":
                    self.shop_screen.handle_event(event)
                elif self.state == "BATTLE" and self.battle:
                    self.battle.handle_event(event)
                elif self.state == "RESULT" and self.result_screen:
                    self.result_screen.handle_event(event)
                elif self.state == "GAME_OVER" and self.game_over_screen:
                    self.game_over_screen.handle_event(event)
                elif self.state == "BONUS_SELECT" and self.bonus_screen:
                    self.bonus_screen.handle_event(event)
            
            self.update()
            self.draw()

if __name__ == "__main__":
    base_path = os.path.dirname(os.path.abspath(__file__))
    words_path = os.path.join(base_path, "words.json")
    game = Game(words_path)
    game.run()
