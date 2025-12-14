import tkinter as tk
from tkinter import messagebox
import socket
import threading
import random
import time

HOST = '127.0.0.1'
PORT = 6666

# --- RENKLER ---
BG_COLOR = "#150202"
BTN_COLOR = "#481a1a"
TEXT_COLOR = "#FFFFFF"
X_COLOR = "#00E5FF"
O_COLOR = "#FF4081"
WIN_GREEN = "#00E676"
WIN_RED = "#FF1744"

class XOXOyunu:
    def __init__(self, root):
        self.root = root
        self.root.title("XOX - Modern")
        self.root.configure(bg=BG_COLOR)
        
        self.turn = 'X' 
        self.board = [""] * 9 
        self.buttons = []
        self.game_mode = "pvp"
        self.my_role = None 
        self.client_socket = None
        self.timer_val = 10
        self.timer_job = None
        self.game_over = False

        top_frame = tk.Frame(root, bg=BG_COLOR)
        top_frame.pack(pady=15)
        
        btn_style = {"font": ("Arial", 10, "bold"), "width": 12, "bd": 0, "fg": "white"}
        tk.Button(top_frame, text="Yanyana (PvP)", command=lambda: self.start_game("pvp"), bg="#875504", **btn_style).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="Bilgisayar", command=lambda: self.start_game("cpu"), bg="#240F54", **btn_style).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="Online Oyna", command=self.connect_online, bg="#0D4910", **btn_style).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="Ayrıl", command=self.go_offline, bg="#840303", **btn_style).pack(side=tk.LEFT, padx=5)
        
        self.lbl_info = tk.Label(root, text="Mod Seçin", font=("Arial", 14, "bold"), bg=BG_COLOR, fg=TEXT_COLOR)
        self.lbl_info.pack(pady=10)
        self.lbl_timer = tk.Label(root, text="Süre: --", font=("Arial", 11), bg=BG_COLOR, fg="#FFD740")
        self.lbl_timer.pack()

        board_frame = tk.Frame(root, bg=BG_COLOR)
        board_frame.pack(pady=15)
        
        for i in range(9):
            btn = tk.Button(board_frame, text="", font=("Arial", 24, "bold"), width=5, height=2,
                            bg=BTN_COLOR, fg=TEXT_COLOR, activebackground="#616161", relief="flat",
                            command=lambda idx=i: self.on_click(idx))
            btn.grid(row=i//3, column=i%3, padx=3, pady=3)
            self.buttons.append(btn)

    def start_game(self, mode):
        if mode in ["pvp", "cpu"] and self.client_socket:
            self.go_offline(sessiz=True)
        self.game_mode = mode
        self.board = [""] * 9
        self.game_over = False
        self.turn = 'X'
        self.timer_val = 10
        for btn in self.buttons:
            btn.config(text="", state="normal", bg=BTN_COLOR)
        self.lbl_timer.config(text="Süre: 10")
        self.stop_timer()

        if mode == "pvp": self.lbl_info.config(text="Mod: Yanyana | Sıra: X")
        elif mode == "cpu": self.lbl_info.config(text="Mod: Bilgisayar | Sıra: X")
        elif mode == "online": self.lbl_info.config(text="Online Bağlandı. Seçim Bekleniyor...")

    def on_click(self, index):
        if self.game_over or self.board[index] != "": return
        if self.game_mode == "cpu" and self.turn == 'O': return 
        if self.game_mode == "online":
            if self.my_role is None: return 
            if self.turn != self.my_role: return 
        
        # 1. Hamleyi Yap ve Ekrana Bas
        self.make_move(index, self.turn)
        
        # 2. Sunucuya Gönder
        if self.game_mode == "online" and self.client_socket:
            try: self.client_socket.send(f"MOVE:{index}$".encode())
            except: pass

        # 3. Şimdi Kontrol Et
        if self.check_winner(): return
        if "" not in self.board: 
            if self.game_mode == "online" and self.client_socket:
                 try: self.client_socket.send(f"OVER:DRAW$".encode())
                 except: pass
            self.end_game("Beraberlik!")
            return

        # 4. Sırayı Değiştir
        self.switch_turn()
        if self.game_mode == "cpu" and self.turn == 'O' and not self.game_over:
            self.root.after(500, self.cpu_move)

    def make_move(self, index, player):
        # Sadece tahtayı güncelle, kontrol yapma (Manuel yapacağız)
        self.board[index] = player
        color = X_COLOR if player == "X" else O_COLOR
        self.buttons[index].config(text=player, fg=color)
        
        # EKRANI GÜNCELLE (ÖNEMLİ)
        self.root.update()
        
        self.stop_timer() 
        # Burada check_winner çağırmıyoruz!

    def switch_turn(self):
        self.turn = 'O' if self.turn == 'X' else 'X'
        if self.game_mode == "online":
            durum = "SENİN SIRAN" if self.turn == self.my_role else "RAKİP BEKLENİYOR"
            self.lbl_info.config(text=f"Ben: {self.my_role} | {durum}")
        else:
            self.lbl_info.config(text=f"Sıra: {self.turn}")
        
        # Sıra değiştiğinde süreyi başlat
        self.start_timer()

    def cpu_move(self):
        empty = [i for i, x in enumerate(self.board) if x == ""]
        if empty:
            self.make_move(random.choice(empty), 'O')
            if self.check_winner(): return
            if "" not in self.board: self.end_game("Beraberlik!"); return
            self.switch_turn()

    def start_timer(self):
        self.timer_val = 10
        self.update_timer()

    def stop_timer(self):
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None

    def update_timer(self):
        if self.game_over: return
        self.lbl_timer.config(text=f"Süre: {self.timer_val}")
        if self.timer_val <= 0:
            self.lbl_timer.config(text="SÜRE DOLDU! Rastgele Oynanıyor...")
            if self.game_mode == "online" and self.turn != self.my_role: return
            empty = [i for i, x in enumerate(self.board) if x == ""]
            if empty: 
                idx = random.choice(empty)
                # Otomatik hamlede on_click çağırıyoruz ki tüm akış çalışsın
                if self.game_mode == "cpu" and self.turn == 'X': self.on_click(idx)
                elif self.game_mode != "cpu": self.on_click(idx)
        else:
            self.timer_val -= 1
            self.timer_job = self.root.after(1000, self.update_timer)

    def check_winner(self):
        wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
        for a,b,c in wins:
            if self.board[a]==self.board[b]==self.board[c] and self.board[a]!="":
                
                # --- RENK BELİRLEME ---
                win_color = WIN_GREEN 
                if self.game_mode == "online" and self.my_role is not None:
                    if self.board[a] == self.my_role: 
                        win_color = WIN_GREEN # Kazanan bensem
                    else: 
                        win_color = WIN_RED   # Kaybettiysem
                
                # --- BOYAMA VE GÜNCELLEME ---
                for idx in [a,b,c]: 
                    self.buttons[idx].config(bg=win_color, fg="white")
                
                self.root.update() # Ekranı boya!
                
                kazanan = self.board[a]
                if self.game_mode == "online" and self.my_role is not None:
                    if kazanan == self.my_role:
                        try: self.client_socket.send(f"OVER:{kazanan}$".encode())
                        except: pass
                
                self.end_game(f"KAZANAN: {kazanan}")
                return True
        return False

    def end_game(self, msg):
        self.game_over = True
        self.stop_timer()
        self.lbl_info.config(text=msg)
        
        self.root.update() 
        time.sleep(0.5)    

        messagebox.showinfo("Oyun Bitti", msg)
        if self.game_mode == "online":
            self.go_offline(sessiz=True)

    def connect_online(self):
        if self.client_socket:
            messagebox.showinfo("Bilgi", " Sunucuya bağlısınız.")
            return
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((HOST, PORT))
            threading.Thread(target=self.receive_data, daemon=True).start()
            self.start_game("online")
        except Exception as e:
            messagebox.showerror("Hata", f"Sunucu yok: {e}")

    def go_offline(self, sessiz=False):
        if self.client_socket:
            try: 
                self.client_socket.shutdown(socket.SHUT_RDWR)
                self.client_socket.close()
            except: pass
        self.client_socket = None
        self.my_role = None
        self.root.title("XOX - Modern")
        if not sessiz: messagebox.showinfo("Mod", "Bağlantı kesildi. Yanyana(PvP) moda geçildi.")
        self.start_game("pvp")

    def secim_penceresi_ac(self):
        win = tk.Toplevel(self.root)
        win.title("Seçimini Yap")
        win.geometry("300x150")
        win.configure(bg=BG_COLOR)
        tk.Label(win, text="Hangisi olmak istersin?", font=("Arial", 12), bg=BG_COLOR, fg=TEXT_COLOR).pack(pady=10)
        tk.Button(win, text="X (Önce Başlar)", font=("Arial", 10, "bold"), bg="#1976D2", fg="white",
                  command=lambda: self.secim_gonder("X", win)).pack(side=tk.LEFT, padx=20, pady=20)
        tk.Button(win, text="O (Sonra Başlar)", font=("Arial", 10, "bold"), bg="#E64A19", fg="white",
                  command=lambda: self.secim_gonder("O", win)).pack(side=tk.RIGHT, padx=20, pady=20)

    def secim_gonder(self, secim, pencere):
        if self.client_socket:
            self.client_socket.send(f"SECIM:{secim}$".encode())
        pencere.destroy()

    def receive_data(self):
        buffer = ""
        while True:
            try:
                if self.client_socket is None: break
                data = self.client_socket.recv(1024).decode()
                if not data: break
                
                buffer += data
                while '$' in buffer:
                    packet, buffer = buffer.split('$', 1)
                    
                    if packet == "SORU:SECIM_YAP":
                        self.root.after(0, self.secim_penceresi_ac)
                    
                    elif packet.startswith("ROLE:"):
                        role = packet.split(":")[1]
                        self.my_role = role
                        self.root.title(f"XOX - BENİM ROLÜM: {role}")
                        if self.turn == self.my_role:
                            durum = "SENİN SIRAN (Başlamak için tıkla)"
                            self.stop_timer()
                        else:
                            durum = "RAKİP BEKLENİYOR"
                        self.lbl_info.config(text=f"Ben: {role} | {durum}")
                    
                    elif packet.startswith("MOVE:"):
                        idx = int(packet.split(":")[1])
                        
                        # 1. Hamleyi yap ve gör
                        self.make_move(idx, self.turn)
                        
                        # 2. Kontrol Et (Kaybeden burada kontrol yapar)
                        if self.check_winner(): 
                            pass # Bitti, boyandı
                        elif "" in self.board: 
                            self.switch_turn()
                    
                    elif packet.startswith("OVER:"):
                        winner = packet.split(":")[1]
                        if winner == "DRAW": 
                            self.end_game("Beraberlik!")
                        else: 
                            # Rakip OVER attıysa, ben kaybettim.
                            # Emin olmak için check_winner çalıştırıp boyayalım
                            self.check_winner()
                            # Eğer check_winner çalışmazsa (gecikme vs) manuel bitir
                            if not self.game_over:
                                self.end_game(f"KAZANAN: {winner}")
            except: 
                self.client_socket = None
                break

if __name__ == "__main__":
    root = tk.Tk()
    app = XOXOyunu(root)
    root.mainloop()