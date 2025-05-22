# main.py
import machine
import ssd1306 
import framebuf
import time
import math
import random
import sys 

# --- Konfiguráció ---
# Kijelző
SCREEN_WIDTH = 72
SCREEN_HEIGHT = 40
I2C_SCL_PIN = 6 
I2C_SDA_PIN = 5 

# Gomb
BUTTON_PIN = 9 

# Játékos
PLAYER_RADIUS = 15 
PLAYER_SPEED = 0.12 
PLAYER_MAX_HEALTH = 5
PLAYER_GUN_COOLDOWN = 8 
PLAYER_HITBOX_RADIUS = 2 

# Ellenség
ENEMY_MAX_HEALTH = 30 # Alapértelmezetten 30
ENEMY_HITBOX_RADIUS = 3 
ENEMY_ATTACK_COOLDOWN_MIN = 30 
ENEMY_ATTACK_COOLDOWN_MAX = 70 
ENEMY_SHIELD_CHANCE = 0.45 # Kicsit növelve az esélyt
ENEMY_SHIELD_DURATION = 130 # Kicsit növelve az időtartamot
ENEMY_SHIELD_GAPS = 3 
ENEMY_SHIELD_SEGMENT_ANGLE_SIZE = (math.pi * 2 / (ENEMY_SHIELD_GAPS * 2)) 
SHIELD_DRAW_OFFSET = 3 # Hány pixellel legyen kijjebb a pajzs az ellenség testétől

# Lövedékek
PROJECTILE_SPEED = 1.8
PROJECTILE_RADIUS = 1 

# Játék
GAME_FPS = 10 
TARGET_FRAME_TIME_MS = 1000 // GAME_FPS
MAX_PROJECTILES_PER_TYPE = 8 

# Pontozás
BASE_HIT_SCORE = 10
MAX_TIME_BONUS = 1000
TARGET_WIN_TIME_S = 45 # Célidő a maximális időbónuszhoz
HEALTH_BONUS_PER_HP = 150

# --- Globális Hardver Objektumok ---
i2c = None
display = None
button = None

# --- Globális Játékállapot Változók ---
player_projectiles = []
enemy_projectiles = []

player_angle = 0.0
player_direction = 1 
player_health = PLAYER_MAX_HEALTH
player_score = 0 # Ez lesz az alap pontszám, amihez a bónuszok jönnek
player_gun_timer = 0

game_start_time_ms = 0 # Játékidő méréséhez

enemy_health = ENEMY_MAX_HEALTH
enemy_is_attacking = False
enemy_attack_type = None
enemy_attack_timer = 0
enemy_attack_state = {}

enemy_shield_active = False
enemy_shield_timer = 0
enemy_shield_style = None 
enemy_shield_current_rotation_offset = 0.0 

CENTER_X = SCREEN_WIDTH // 2
CENTER_Y = SCREEN_HEIGHT // 2

# --- Segédfüggvények (változatlanok az előzőhöz képest, rövidítem a megjelenítést) ---
def draw_pixel_circle(fb, center_x, center_y, radius, color=1):
    x = radius; y = 0; err = 1 - x
    while x >= y:
        fb.pixel(center_x + x, center_y + y, color); fb.pixel(center_x + y, center_y + x, color)
        fb.pixel(center_x - y, center_y + x, color); fb.pixel(center_x - x, center_y + y, color)
        fb.pixel(center_x - x, center_y - y, color); fb.pixel(center_x - y, center_y - x, color)
        fb.pixel(center_x + y, center_y - x, color); fb.pixel(center_x + x, center_y - y, color)
        y += 1
        if err < 0: err += 2 * y + 1
        else: x -= 1; err += 2 * (y - x) + 1

def draw_arc(fb, cx, cy, r, start_angle_rad, end_angle_rad, color=1):
    sa_norm = (start_angle_rad + 2 * math.pi) % (2 * math.pi)
    ea_norm = (end_angle_rad + 2 * math.pi) % (2 * math.pi)
    arc_length = (ea_norm - sa_norm + 2 * math.pi) % (2 * math.pi)
    if arc_length == 0 and start_angle_rad != end_angle_rad : arc_length = 2*math.pi
    num_steps = int(arc_length * r / 1.0); 
    if num_steps < 2: num_steps = 2
    angle_step = arc_length / num_steps
    for i in range(num_steps + 1):
        angle = (sa_norm + i * angle_step) % (2 * math.pi)
        x = cx + int(r * math.cos(angle)); y = cy + int(r * math.sin(angle))
        if 0 <= x < SCREEN_WIDTH and 0 <= y < SCREEN_HEIGHT: fb.pixel(x, y, color)

def distance_sq(x1, y1, x2, y2): return (x1 - x2)**2 + (y1 - y2)**2

def is_point_on_arc_segment(px, py, cx, cy, radius, arc_start_angle, arc_end_angle, tolerance=1.5):
    dist_sq_from_center = distance_sq(px, py, cx, cy)
    if not ((radius - tolerance)**2 <= dist_sq_from_center <= (radius + tolerance)**2): return False
    angle_to_point = (math.atan2(py - cy, px - cx) + 2 * math.pi) % (2 * math.pi)
    s_angle_norm = (arc_start_angle + 2 * math.pi) % (2 * math.pi)
    e_angle_norm = (arc_end_angle + 2 * math.pi) % (2 * math.pi)
    if s_angle_norm <= e_angle_norm: return s_angle_norm <= angle_to_point <= e_angle_norm
    else: return angle_to_point >= s_angle_norm or angle_to_point <= e_angle_norm

# --- Hardver Inicializálás (változatlan) ---
# --- Hardver Inicializálás (JAVÍTOTT) ---
def initialize_hardware():
    global i2c, display, button
    try:
        scl_pin_obj = machine.Pin(I2C_SCL_PIN)
        sda_pin_obj = machine.Pin(I2C_SDA_PIN)
        i2c = machine.I2C(0, scl=scl_pin_obj, sda=sda_pin_obj, freq=400000)
        display = ssd1306.SSD1306_I2C(SCREEN_WIDTH, SCREEN_HEIGHT, i2c)
        button = machine.Pin(BUTTON_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
        print("Hardver inicializálva.")
        return True
    except Exception as e:
        print(f"Hardver inicializálási hiba: {e}")
        # A 'sys' modult a fájl tetején importáltuk már
        if 'micropython' not in sys.implementation.name:
            # Ez a blokk csak akkor futna le, ha NEM MicroPython környezetben vagyunk
            class DummyDisplay:
                def __init__(self, width, height):
                    self.width = width
                    self.height = height
                    self.fb = framebuf.FrameBuffer(bytearray(width * height // 8), width, height, framebuf.MONO_HLSB)
                
                def fill(self, c): # Külön sorban
                    self.fb.fill(c)
                
                def pixel(self, x, y, c): # Külön sorban
                    self.fb.pixel(x,y,c)
                
                def text(self, s, x, y, c=1): # Külön sorban
                    self.fb.text(s,x,y,c)
                
                def show(self): # Külön sorban
                    pass 
            
            display = DummyDisplay(SCREEN_WIDTH, SCREEN_HEIGHT)
            
            class DummyButton: 
                def value(self): 
                    return 1 # Nincs lenyomva
            button = DummyButton()
            
            print("Dummy hardverrel inicializálva teszteléshez.")
            return True 
            
        return False

# --- Játékállapot Visszaállítása ---
def reset_game_state():
    global player_health, enemy_health, player_score, player_angle, player_direction, player_gun_timer
    global player_projectiles, enemy_projectiles, game_start_time_ms
    global enemy_is_attacking, enemy_attack_type, enemy_attack_timer, enemy_attack_state
    global enemy_shield_active, enemy_shield_timer, enemy_shield_style, enemy_shield_current_rotation_offset

    player_health = PLAYER_MAX_HEALTH
    player_angle = 0.0
    player_direction = 1
    player_score = 0 # Alap pontszám nullázása
    player_gun_timer = PLAYER_GUN_COOLDOWN // 2 

    enemy_health = ENEMY_MAX_HEALTH
    
    player_projectiles.clear()
    enemy_projectiles.clear()
    
    enemy_is_attacking = False
    enemy_attack_timer = random.randint(ENEMY_ATTACK_COOLDOWN_MIN // 2, ENEMY_ATTACK_COOLDOWN_MAX // 2)
    enemy_attack_type = None
    enemy_attack_state.clear()

    enemy_shield_active = False
    enemy_shield_timer = 0
    enemy_shield_style = None
    enemy_shield_current_rotation_offset = random.uniform(0, 2 * math.pi)
    
    game_start_time_ms = time.ticks_ms() # Játékidő mérésének indítása
    print("Játékállapot visszaállítva.")

# --- Frissítési Funkciók (Player, Fire_Enemy, Enemy_Shield, Activate_Enemy_Shield változatlanok, rövidítem) ---
def update_player():
    global player_angle, player_gun_timer
    player_angle = (player_angle + player_direction * PLAYER_SPEED) % (2 * math.pi)
    player_gun_timer -= 1
    if player_gun_timer <= 0:
        if len(player_projectiles) < MAX_PROJECTILES_PER_TYPE:
            px = CENTER_X + PLAYER_RADIUS*math.cos(player_angle); py = CENTER_Y + PLAYER_RADIUS*math.sin(player_angle)
            angle_to_center = math.atan2(CENTER_Y - py, CENTER_X - px)
            player_projectiles.append({'x':px,'y':py,'vx':math.cos(angle_to_center)*PROJECTILE_SPEED,'vy':math.sin(angle_to_center)*PROJECTILE_SPEED})
        player_gun_timer = PLAYER_GUN_COOLDOWN

def fire_enemy_projectile(start_x, start_y, target_x, target_y):
    if len(enemy_projectiles) < MAX_PROJECTILES_PER_TYPE:
        angle = math.atan2(target_y - start_y, target_x - start_x)
        enemy_projectiles.append({'x':start_x,'y':start_y,'vx':math.cos(angle)*PROJECTILE_SPEED*0.8,'vy':math.sin(angle)*PROJECTILE_SPEED*0.8})

def update_enemy_shield():
    global enemy_shield_active, enemy_shield_timer
    if enemy_shield_active:
        enemy_shield_timer -=1
        if enemy_shield_timer <= 0: enemy_shield_active = False; # print("Ellenség pajzsa LE")

def activate_enemy_shield():
    global enemy_shield_active, enemy_shield_timer, enemy_shield_style, enemy_shield_current_rotation_offset
    if not enemy_shield_active and random.random() < ENEMY_SHIELD_CHANCE:
        enemy_shield_active = True; enemy_shield_timer = ENEMY_SHIELD_DURATION
        enemy_shield_style = random.choice(["C", "SEGMENTED"])
        enemy_shield_current_rotation_offset = random.uniform(0, 2 * math.pi)
        # print(f"Ellenség pajzsa BE: {enemy_shield_style}")

def update_enemy(): # (Logika változatlan, csak hívja a shieldet)
    global enemy_is_attacking, enemy_attack_type, enemy_attack_timer, enemy_attack_state
    if not enemy_is_attacking:
        enemy_attack_timer -= 1
        if enemy_attack_timer <= 0:
            enemy_is_attacking = True; attack_types = ["STRAIGHT","DIAGONAL","TARGETED_ARC","ROTATING_BARRAGE"]
            enemy_attack_type = random.choice(attack_types) #; print(f"Ellenség támad: {enemy_attack_type}")
            if enemy_attack_type == "STRAIGHT": enemy_attack_state = {'fired': False}
            elif enemy_attack_type == "DIAGONAL": enemy_attack_state = {'fired': False}
            elif enemy_attack_type == "TARGETED_ARC":
                pred_time_factor = PLAYER_RADIUS/(PROJECTILE_SPEED*0.8)
                pred_angle = (player_angle + player_direction*PLAYER_SPEED*(pred_time_factor*0.3*GAME_FPS))%(2*math.pi)
                txp=CENTER_X+PLAYER_RADIUS*math.cos(pred_angle); typ=CENTER_Y+PLAYER_RADIUS*math.sin(pred_angle)
                base_angle = math.atan2(typ-CENTER_Y,txp-CENTER_X)
                enemy_attack_state = {'projectiles_to_fire':3,'arc_span_rad':math.radians(45),'current_projectile_idx':0,'base_angle':base_angle,'fire_interval_timer':0,'fire_interval':4}
            elif enemy_attack_type == "ROTATING_BARRAGE":
                enemy_attack_state = {'current_angle':random.uniform(0,2*math.pi),'angle_step':math.radians(30),'projectiles_fired_count':0,'total_projectiles_in_burst':int(360/30),'fire_interval_timer':0,'fire_interval':3}
    else: 
        state = enemy_attack_state
        if enemy_attack_type == "STRAIGHT":
            if not state['fired']:
                fire_enemy_projectile(CENTER_X,CENTER_Y,CENTER_X,0); fire_enemy_projectile(CENTER_X,CENTER_Y,CENTER_X,SCREEN_HEIGHT-1)
                fire_enemy_projectile(CENTER_X,CENTER_Y,0,CENTER_Y); fire_enemy_projectile(CENTER_X,CENTER_Y,SCREEN_WIDTH-1,CENTER_Y)
                state['fired']=True; enemy_is_attacking=False; enemy_attack_timer=random.randint(ENEMY_ATTACK_COOLDOWN_MIN,ENEMY_ATTACK_COOLDOWN_MAX); activate_enemy_shield()
        elif enemy_attack_type == "DIAGONAL":
            if not state['fired']:
                angles = [math.pi/4,3*math.pi/4,5*math.pi/4,7*math.pi/4]
                for ang in angles: fire_enemy_projectile(CENTER_X,CENTER_Y,CENTER_X+SCREEN_WIDTH*math.cos(ang),CENTER_Y+SCREEN_HEIGHT*math.sin(ang))
                state['fired']=True; enemy_is_attacking=False; enemy_attack_timer=random.randint(ENEMY_ATTACK_COOLDOWN_MIN,ENEMY_ATTACK_COOLDOWN_MAX); activate_enemy_shield()
        elif enemy_attack_type == "TARGETED_ARC":
            state['fire_interval_timer']-=1
            if state['fire_interval_timer']<=0 and state['current_projectile_idx']<state['projectiles_to_fire']:
                num_arc=state['projectiles_to_fire']; ang_off_step=state['arc_span_rad']/(num_arc-1) if num_arc>1 else 0
                curr_off=(state['current_projectile_idx']-(num_arc-1)/2)*ang_off_step; final_ang=state['base_angle']+curr_off
                fire_enemy_projectile(CENTER_X,CENTER_Y,CENTER_X+SCREEN_WIDTH*math.cos(final_ang),CENTER_Y+SCREEN_HEIGHT*math.sin(final_ang))
                state['current_projectile_idx']+=1; state['fire_interval_timer']=state['fire_interval']
            if state['current_projectile_idx']>=state['projectiles_to_fire']:
                enemy_is_attacking=False; enemy_attack_timer=random.randint(ENEMY_ATTACK_COOLDOWN_MIN,ENEMY_ATTACK_COOLDOWN_MAX); activate_enemy_shield()
        elif enemy_attack_type == "ROTATING_BARRAGE":
            state['fire_interval_timer']-=1
            if state['fire_interval_timer']<=0 and state['projectiles_fired_count']<state['total_projectiles_in_burst']:
                fire_enemy_projectile(CENTER_X,CENTER_Y,CENTER_X+SCREEN_WIDTH*math.cos(state['current_angle']),CENTER_Y+SCREEN_HEIGHT*math.sin(state['current_angle']))
                state['current_angle']=(state['current_angle']+state['angle_step'])%(2*math.pi); state['projectiles_fired_count']+=1; state['fire_interval_timer']=state['fire_interval']
            if state['projectiles_fired_count']>=state['total_projectiles_in_burst']:
                enemy_is_attacking=False; enemy_attack_timer=random.randint(ENEMY_ATTACK_COOLDOWN_MIN,ENEMY_ATTACK_COOLDOWN_MAX); activate_enemy_shield()
    update_enemy_shield()


def update_projectiles():
    global player_health, enemy_health, player_score # player_score itt alap pontszámként módosul

    # Játékos lövedékei
    for p in list(player_projectiles):
        p['x'] += p['vx']; p['y'] += p['vy']
        if not (0 <= p['x'] < SCREEN_WIDTH and 0 <= p['y'] < SCREEN_HEIGHT):
            player_projectiles.remove(p); continue
        
        if distance_sq(p['x'], p['y'], CENTER_X, CENTER_Y) < (ENEMY_HITBOX_RADIUS + PROJECTILE_RADIUS)**2:
            projectile_hits_target = True 
            if enemy_shield_active:
                shield_collision_radius = ENEMY_HITBOX_RADIUS + SHIELD_DRAW_OFFSET # Ugyanaz a sugár, mint a rajzolásnál
                projectile_blocked_by_shield = False
                if enemy_shield_style == "C":
                    gap_size_rad = math.pi / 2 
                    shield_actual_start_angle = (enemy_shield_current_rotation_offset + gap_size_rad) % (2 * math.pi)
                    shield_actual_end_angle = enemy_shield_current_rotation_offset 
                    if is_point_on_arc_segment(p['x'], p['y'], CENTER_X, CENTER_Y, shield_collision_radius, 
                                             shield_actual_start_angle, shield_actual_end_angle, PROJECTILE_RADIUS + 1): # Kicsit nagyobb tolerancia
                        projectile_blocked_by_shield = True
                elif enemy_shield_style == "SEGMENTED":
                    for i in range(ENEMY_SHIELD_GAPS):
                        segment_start = (enemy_shield_current_rotation_offset + i * 2 * ENEMY_SHIELD_SEGMENT_ANGLE_SIZE) % (2 * math.pi)
                        segment_end = (segment_start + ENEMY_SHIELD_SEGMENT_ANGLE_SIZE) % (2 * math.pi)
                        if is_point_on_arc_segment(p['x'], p['y'], CENTER_X, CENTER_Y, shield_collision_radius,
                                                 segment_start, segment_end, PROJECTILE_RADIUS + 1):
                            projectile_blocked_by_shield = True; break 

                if projectile_blocked_by_shield:
                    projectile_hits_target = False 
                    # print("Pajzs blokkolt!") # Debug célra
            
            if projectile_hits_target:
                enemy_health -= 1
                player_score += BASE_HIT_SCORE # Csak az alap pontszámot növeljük itt
            
            if p in player_projectiles: player_projectiles.remove(p) 
            continue

    # Ellenség lövedékei
    player_pos_x = CENTER_X + PLAYER_RADIUS * math.cos(player_angle)
    player_pos_y = CENTER_Y + PLAYER_RADIUS * math.sin(player_angle)
    for p in list(enemy_projectiles):
        p['x'] += p['vx']; p['y'] += p['vy']
        if not (0 <= p['x'] < SCREEN_WIDTH and 0 <= p['y'] < SCREEN_HEIGHT):
            enemy_projectiles.remove(p); continue
        if distance_sq(p['x'], p['y'], player_pos_x, player_pos_y) < (PLAYER_HITBOX_RADIUS + PROJECTILE_RADIUS)**2:
            player_health -= 1; enemy_projectiles.remove(p); continue

# --- Rajzolási Funkciók ---
def draw_game():
    display.fill(0) 
    player_draw_x = int(CENTER_X + PLAYER_RADIUS*math.cos(player_angle))
    player_draw_y = int(CENTER_Y + PLAYER_RADIUS*math.sin(player_angle))
    display.fill_rect(player_draw_x - 1, player_draw_y - 1, 3, 3, 1) 
    draw_pixel_circle(display, CENTER_X, CENTER_Y, ENEMY_HITBOX_RADIUS + 1, 1)

    if enemy_shield_active:
        shield_draw_radius = ENEMY_HITBOX_RADIUS + SHIELD_DRAW_OFFSET # Pajzs kijjebb
        if enemy_shield_style == "C":
            gap_size_rad = math.pi / 2 
            shield_arc_S = (enemy_shield_current_rotation_offset + gap_size_rad) % (2 * math.pi)
            shield_arc_E = enemy_shield_current_rotation_offset 
            draw_arc(display, CENTER_X, CENTER_Y, shield_draw_radius, shield_arc_S, shield_arc_E, 1)
        elif enemy_shield_style == "SEGMENTED":
            for i in range(ENEMY_SHIELD_GAPS):
                segment_s = (enemy_shield_current_rotation_offset + i * 2 * ENEMY_SHIELD_SEGMENT_ANGLE_SIZE) % (2 * math.pi)
                segment_e = (segment_s + ENEMY_SHIELD_SEGMENT_ANGLE_SIZE) % (2 * math.pi)
                draw_arc(display, CENTER_X, CENTER_Y, shield_draw_radius, segment_s, segment_e, 1)

    for p in player_projectiles: display.pixel(int(p['x']), int(p['y']), 1)
    for p in enemy_projectiles: display.pixel(int(p['x']), int(p['y']), 1) 
    for i in range(player_health): display.fill_rect(i * 3, 0, 2, 2, 1)

    # Ellenség életerőcsík (JAVÍTVA: balról jobbra fogy)
    enemy_hp_bar_max_w = SCREEN_WIDTH // 3
    enemy_hp_bar_current_w = 0
    if ENEMY_MAX_HEALTH > 0:
        enemy_hp_bar_current_w = int((enemy_health / ENEMY_MAX_HEALTH) * enemy_hp_bar_max_w)
    
    # Keret mindig látszik
    display.rect(SCREEN_WIDTH - enemy_hp_bar_max_w - 1, 0, enemy_hp_bar_max_w, 3, 1) 
    if enemy_hp_bar_current_w > 0: # Csak akkor töltjük ki, ha van mit
      display.fill_rect(SCREEN_WIDTH - enemy_hp_bar_max_w -1 , 1, enemy_hp_bar_current_w, 1, 1) # Balról indul
    
    # Pontszám (csak az alap, játék közben) - most nem jelenítjük meg a helyszűke miatt játék közben
    # score_text_ingame = str(player_score)
    # display.text(score_text_ingame, CENTER_X - (len(score_text_ingame)*8)//2, SCREEN_HEIGHT - 9, 1)
    
    display.show() 

# --- Játékmenet Ciklusa (belső) ---
def game_loop_internal(): # Visszaadja: (győzelem_állapota, játékidő_ms, megmaradt_hp)
    reset_game_state() 
    last_button_state = button.value() 

    while True: 
        current_time_ms_loop_start = time.ticks_ms()
        current_button_state = button.value()
        if last_button_state == 1 and current_button_state == 0:
            global player_direction
            player_direction *= -1
        last_button_state = current_button_state
        
        update_player(); update_enemy(); update_projectiles()
        draw_game()

        game_over = False
        won = False
        if player_health <= 0:
            game_over = True; won = False
        elif enemy_health <= 0:
            game_over = True; won = True
        
        if game_over:
            game_duration_ms = time.ticks_diff(time.ticks_ms(), game_start_time_ms)
            return won, game_duration_ms, player_health # Visszaadjuk a játékidőt és a HP-t is

        elapsed_ms = time.ticks_diff(time.ticks_ms(), current_time_ms_loop_start)
        sleep_duration_ms = TARGET_FRAME_TIME_MS - elapsed_ms
        if sleep_duration_ms > 0: time.sleep_ms(sleep_duration_ms)

# --- Fő Belépési Pont és Újraindítási Logika ---
def main_entry():
    global player_score # Itt fogjuk a teljes pontszámot tárolni a bónuszokkal
    
    while True: 
        game_result, duration_ms, final_hp_player = game_loop_internal() 
        
        current_base_score = player_score # Ez a játék során szerzett alap pontszám
        final_total_score = current_base_score
        
        if game_result: # Játékos nyert
            # Idő bónusz
            duration_s = duration_ms / 1000.0
            time_bonus = 0
            if duration_s <= TARGET_WIN_TIME_S:
                time_bonus = MAX_TIME_BONUS
            elif duration_s <= TARGET_WIN_TIME_S * 2: # Dupla célidőig adunk csökkenő bónuszt
                time_bonus = int(MAX_TIME_BONUS * (1 - (duration_s - TARGET_WIN_TIME_S) / TARGET_WIN_TIME_S))
            
            final_total_score += max(0, time_bonus) # Biztosítjuk, hogy ne legyen negatív bónusz

            # Élet bónusz
            health_bonus = final_hp_player * HEALTH_BONUS_PER_HP
            final_total_score += health_bonus
        else: # Játékos vesztett, nincs bónusz, csak az alap pontszám
            pass 
            # A player_score már az alap pontszámot tartalmazza
        
        player_score = final_total_score # Frissítjük a globális player_score-t a megjelenítéshez

        display.fill(0)
        title_text = ""
        if game_result: title_text = "GYOZELEM!"
        else: title_text = "VEGE"
        display.text(title_text, (SCREEN_WIDTH - len(title_text)*8)//2 , 5, 1) # Kicsit feljebb a főcím
        
        score_msg = "Pont:" + str(player_score)
        display.text(score_msg, (SCREEN_WIDTH - len(score_msg)*8)//2, 15, 1)
        
        # JAVÍTÁS: "Ujra: GOMB" középre igazítása
        restart_text = "Ujra:GOMB"
        display.text(restart_text, (SCREEN_WIDTH - len(restart_text)*8)//2, 28, 1) # Kicsit lejjebb a felirat
        display.show()

        time.sleep_ms(300) 
        while button.value() == 0: time.sleep_ms(50)
        while button.value() == 1: time.sleep_ms(50)

# --- Program Indítása ---
if __name__ == '__main__':
    if not initialize_hardware(): print("Hardverhiba, program leáll.")
    else:
        try: main_entry()
        except Exception as e:
            print(f"Kritikus futási hiba: {e}"); sys.print_exception(e)
            if display: 
                display.fill(0); display.text("HIBA!", 0,0,1)
                # A teljes hibaüzenet kiírása általában nem fér ki, és bonyolult
                # error_lines = str(e).split('\n')
                # y_pos = 10
                # for line in error_lines:
                #    if y_pos < SCREEN_HEIGHT - 8:
                #        display.text(line[:SCREEN_WIDTH//8], 0, y_pos, 1) # Vágás, ha túl hosszú
                #        y_pos +=10
                display.show()
        finally: print("Program befejezve.")