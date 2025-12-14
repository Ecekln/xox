import socket
import threading
import time

HOST = '127.0.0.1'
PORT = 6666

clients = []
first_player_choice = None 

def handle_client(client_socket):
    global first_player_choice
    while True:
        try:
            message = client_socket.recv(1024).decode()
            if not message: 
                disconnect_client(client_socket)
                break
            
            if message.startswith("SECIM:"):
                clean_msg = message.replace("$", "")
                choice = clean_msg.split(":")[1]
                first_player_choice = choice
                print(f"[SEÇİM] 1. Oyuncu {choice} olmak istedi.")
                client_socket.send(f"ROLE:{choice}$".encode())
                
            elif message.startswith("MOVE:") or message.startswith("OVER:"):
                broadcast(message.encode(), client_socket)
                
        except: 
            disconnect_client(client_socket)
            break

def broadcast(message, sender_socket):
    for client in clients:
        if client != sender_socket:
            try:
                client.send(message)
            except:
                disconnect_client(client)

def disconnect_client(client_socket):
    global first_player_choice
    if client_socket in clients:
        clients.remove(client_socket)
        try: client_socket.close()
        except: pass
    
    # Kalan kişi sayısı 0 ise hafızayı sil
    if len(clients) == 0:
        first_player_choice = None
        print("[SIFIRLANDI] Oda tamamen boşaldı.")

def start_server():
    global first_player_choice
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try: server.bind((HOST, PORT))
    except OSError: print("HATA: Port dolu!"); return

    server.listen(5) # Kuyruğu biraz artırdık
    print(f"[XOX SUNUCU] {HOST}:{PORT} - Kapasite Korumalı Mod...")

    while True:
        try:
            client_socket, addr = server.accept()
            
            # --- YENİ KORUMA SİSTEMİ ---
            # Eğer yeni biri geldiğinde içeride zaten 2 (veya daha fazla) kişi görünüyorsa
            # Bu "Zombi" durumudur. Hepsini at ve sıfırdan başla.
            if len(clients) >= 2:
                print(f"[UYARI] Kapasite dolu ({len(clients)}). Zombiler temizleniyor...")
                for c in clients:
                    try: c.close()
                    except: pass
                clients.clear()
                first_player_choice = None
                print("[TEMİZLİK] Oda zorla boşaltıldı. Yeni oyuncu 1. sıraya alındı.")

            # Artık listeye ekle
            clients.append(client_socket)
            print(f"[BAĞLANTI] Oyuncu geldi. Güncel Toplam: {len(clients)}")
            
            # 1. Oyuncu İşlemleri
            if len(clients) == 1:
                # Hafızayı garanti sil (Eskiden kalma seçim olmasın)
                first_player_choice = None
                
                client_socket.send("SORU:SECIM_YAP$".encode())
                threading.Thread(target=handle_client, args=(client_socket,)).start()
                
            # 2. Oyuncu İşlemleri
            elif len(clients) == 2:
                threading.Thread(target=ikinci_oyuncuyu_yonet, args=(client_socket,)).start()
            
        except Exception as e:
            print(f"Hata: {e}")

def ikinci_oyuncuyu_yonet(client_socket):
    global first_player_choice
    # 1. Oyuncu seçim yapana kadar bekle
    while first_player_choice is None:
        if len(clients) < 2: return
        time.sleep(0.5)
    
    my_role = "O" if first_player_choice == "X" else "X"
    print(f"[ATAMA] 2. Oyuncuya {my_role} verildi.")
    
    try:
        client_socket.send(f"ROLE:{my_role}$".encode())
        handle_client(client_socket)
    except:
        disconnect_client(client_socket)

if __name__ == "__main__":
    start_server()