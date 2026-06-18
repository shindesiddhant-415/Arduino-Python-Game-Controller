import tkinter as tk
from tkinter import ttk, scrolledtext
import serial
import serial.tools.list_ports
import threading, socket, time, queue
from flask import Flask, request, jsonify, render_template_string
import logging

try:
    import pydirectinput as kb
    kb.FAILSAFE = False
    kb.PAUSE = 0
except:
    import pyautogui as kb
    kb.FAILSAFE = False
    kb.PAUSE = 0

# fix slow flask startup
try:
    from werkzeug.serving import WSGIRequestHandler
    WSGIRequestHandler.address_string = lambda self: self.client_address[0]
except:
    pass

app = Flask(__name__)
logging.getLogger('werkzeug').setLevel(logging.ERROR)

class KeyMgr:
    def __init__(self):
        self.pressed = {}
    
    def press(self, k):
        count = self.pressed.get(k, 0)
        self.pressed[k] = count + 1
        if self.pressed[k] == 1:
            kb.keyDown(k)
            
    def release(self, k):
        count = self.pressed.get(k, 0)
        if count > 0:
            self.pressed[k] = count - 1
            if self.pressed[k] == 0:
                kb.keyUp(k)

km = KeyMgr()

class JoyLogic:
    def __init__(self, m="WASD"):
        self.enabled = True
        self.mode = m
        self.min_val = 400
        self.max_val = 600
        self.active = set()
        
    def get_keys(self):
        if self.mode == "Arrow Keys":
            return {'up': 'up', 'down': 'down', 'left': 'left', 'right': 'right'}
        return {'up': 'w', 'down': 's', 'left': 'a', 'right': 'd'}

    def press(self, k):
        mapper = self.get_keys()
        val = mapper.get(k)
        if val and val not in self.active:
            km.press(val)
            self.active.add(val)
            return True
        return False

    def release(self, k):
        mapper = self.get_keys()
        val = mapper.get(k)
        if val and val in self.active:
            km.release(val)
            self.active.remove(val)
            return True
        return False

    def release_all(self):
        for val in list(self.active):
            km.release(val)
        self.active.clear()

    def update(self, x, y):
        if not self.enabled:
            self.release_all()
            return

        # x
        if x < self.min_val: 
            self.press('left')
            self.release('right')
        elif x > self.max_val: 
            self.press('right')
            self.release('left')
        else:
            self.release('left')
            self.release('right')

        # y
        if y < self.min_val: 
            self.press('up')
            self.release('down')
        elif y > self.max_val: 
            self.press('down')
            self.release('up')
        else:
            self.release('up')
            self.release('down')

j_in = JoyLogic(m="WASD")
p_in = JoyLogic(m="Arrow Keys")
q = queue.Queue()

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        return s.getsockname()[0]
    except:
        return '127.0.0.1'
    finally:
        s.close()

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;600&display=swap');
    body { 
        display: flex; flex-direction: column; align-items: center; justify-content: center; 
        height: 100vh; margin: 0; background: #111; color: #fff; font-family: 'Outfit', sans-serif;
        user-select: none; -webkit-user-select: none; overscroll-behavior: none; 
    }
    h2 { font-weight: 300; letter-spacing: 2px; color: #aaa; margin-bottom: 50px; }
    
    .base {
        padding: 40px; border-radius: 50%;
        background: #222;
        box-shadow: inset 0 0 20px #000, 0 10px 30px #000;
    }

    .dpad { display: grid; grid-template-columns: 75px 75px 75px; grid-template-rows: 75px 75px 75px; position: relative;}
    .dpad::after {
        content: ''; grid-column: 2; grid-row: 2;
        background: #333; z-index: 1; border: 1px solid #444;
    }

    .btn { 
        background: #333; border: 1px solid #444; color: #888; font-size: 28px; 
        display: flex; align-items: center; justify-content: center; cursor: pointer; 
        touch-action: none; z-index: 2; position: relative;
    }

    .up { grid-column: 2; grid-row: 1; border-radius: 10px 10px 0 0; border-bottom: none; }
    .down { grid-column: 2; grid-row: 3; border-radius: 0 0 10px 10px; border-top: none; }
    .left { grid-column: 1; grid-row: 2; border-radius: 10px 0 0 10px; border-right: none; }
    .right { grid-column: 3; grid-row: 2; border-radius: 0 10px 10px 0; border-left: none; }

    .btn.active { 
        background: #111; color: #0fc;
        text-shadow: 0 0 10px #0fc;
        transform: scale(0.95);
    }
</style>
</head>
<body>
    <h2>Phone Remote</h2>
    <div class="base">
        <div class="dpad">
            <div class="btn up">▲</div>
            <div class="btn left">◄</div>
            <div class="btn right">►</div>
            <div class="btn down">▼</div>
        </div>
    </div>
    <script>
        function send_cmd(dir, state) {
            if (navigator.sendBeacon) {
                navigator.sendBeacon("/api/c?d=" + dir + "&s=" + state);
            } else {
                fetch("/api/c?d=" + dir + "&s=" + state).then(r => r.text()).catch(e => console.log(e));
            }
        }

        function hook(cls, d) {
            let b = document.querySelector('.' + cls);
            let p = false;
            
            let press = (e) => { 
                if(e.cancelable) e.preventDefault(); 
                if(!p){ p=true; b.classList.add('active'); send_cmd(d, '1'); } 
            };
            let release = (e) => { 
                if(e.cancelable) e.preventDefault(); 
                if(p){ p=false; b.classList.remove('active'); send_cmd(d, '0'); } 
            };

            b.addEventListener('touchstart', press, {passive: false});
            b.addEventListener('touchend', release, {passive: false});
            b.addEventListener('mousedown', press);
            b.addEventListener('mouseup', release);
            b.addEventListener('mouseleave', release);
        }

        window.onload = () => {
            hook('up', 'up'); hook('down', 'down'); hook('left', 'left'); hook('right', 'right');
        };
    </script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/api/c", methods=['GET', 'POST'])
def c_api():
    if not p_in.enabled:
        return jsonify({"err": "disabled"}), 403
        
    d = request.args.get('d')
    s = request.args.get('s')
    
    if d in ['up', 'down', 'left', 'right']:
        if s == '1':
            if p_in.press(d):
                q.put(f"phone press {d}")
        elif s == '0':
            if p_in.release(d):
                q.put(f"phone rel {d}")
        return '', 204
    return jsonify({"err": "bad"}), 400


class App:
    def __init__(self, root):
        self.w = root
        self.w.title("Controller Hub")
        self.w.geometry("480x560")
        
        ttk.Style().theme_use('clam')
        
        self.ser = None
        self.t = None
        self.running = False
        self.flask_t = None
        
        self.btn_spc = False
        self.btn_shf = False
        self.btn_f = False
        self.btn_esc = False
        
        self.build_ui()
        self.start_server()
        self.check_q()

    def build_ui(self):
        mf = ttk.Frame(self.w, padding=10)
        mf.pack(fill=tk.BOTH, expand=True)
        
        # com port stuff
        f1 = ttk.LabelFrame(mf, text="Serial Setup", padding=10)
        f1.pack(fill=tk.X, pady=5)
        
        ttk.Label(f1, text="COM:").grid(row=0, column=0, padx=5, pady=5)
        self.p_var = tk.StringVar()
        self.cbox = ttk.Combobox(f1, textvariable=self.p_var, width=12)
        self.cbox.grid(row=0, column=1)
        self.find_ports()
        
        ttk.Button(f1, text="Refresh", command=self.find_ports).grid(row=0, column=2, padx=5)
        self.c_btn = ttk.Button(f1, text="Connect", command=self.toggle)
        self.c_btn.grid(row=0, column=3, padx=5)
        
        self.s_lbl = ttk.Label(f1, text="Not connected", foreground="red")
        self.s_lbl.grid(row=1, column=0, columnspan=4, sticky=tk.W)
        
        # values
        f2 = ttk.LabelFrame(mf, text="Live Data", padding=10)
        f2.pack(fill=tk.X, pady=5)
        
        self.lx = ttk.Label(f2, text="X: 0", font=("Consolas", 12))
        self.lx.grid(row=0, column=0, padx=15)
        self.ly = ttk.Label(f2, text="Y: 0", font=("Consolas", 12))
        self.ly.grid(row=0, column=1, padx=15)
        
        # settings
        f3 = ttk.LabelFrame(mf, text="Settings", padding=10)
        f3.pack(fill=tk.X, pady=5)
        
        self.en_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(f3, text="Enable Input", variable=self.en_var, command=self.upd_set).grid(row=0, column=0, columnspan=2, sticky=tk.W)
        
        ttk.Label(f3, text="Joy Mode:").grid(row=1, column=0, sticky=tk.W)
        self.m1 = tk.StringVar(value="WASD")
        ttk.Combobox(f3, textvariable=self.m1, values=["WASD", "Arrow Keys"], state="readonly", width=10).grid(row=1, column=1)
        self.m1.trace_add('write', lambda *a: self.upd_set())

        ttk.Label(f3, text="Phone Mode:").grid(row=2, column=0, sticky=tk.W)
        self.m2 = tk.StringVar(value="Arrow Keys")
        ttk.Combobox(f3, textvariable=self.m2, values=["WASD", "Arrow Keys"], state="readonly", width=10).grid(row=2, column=1)
        self.m2.trace_add('write', lambda *a: self.upd_set())
        
        self.dead_v = tk.IntVar(value=100)
        ttk.Label(f3, text="Deadzone:").grid(row=3, column=0, sticky=tk.W)
        ttk.Scale(f3, from_=10, to=300, variable=self.dead_v, command=self.upd_dead).grid(row=3, column=1, sticky=tk.EW)

        # server info
        f4 = ttk.LabelFrame(mf, text="Web Remote", padding=10)
        f4.pack(fill=tk.X, pady=5)
        ttk.Label(f4, text=f"Go to: http://{get_ip()}:5000", foreground="blue").pack(anchor=tk.W)
        
        # logs
        self.txt = scrolledtext.ScrolledText(mf, height=8, font=("Consolas", 9), state='disabled')
        self.txt.pack(fill=tk.BOTH, expand=True, pady=10)
        
    def find_ports(self):
        prts = serial.tools.list_ports.comports()
        self.cbox['values'] = [p.device for p in prts]
        if self.cbox['values']:
            self.cbox.current(0)

    def write_log(self, m):
        self.txt.config(state='normal')
        self.txt.insert(tk.END, m + "\n")
        self.txt.see(tk.END)
        self.txt.config(state='disabled')

    def check_q(self):
        while not q.empty():
            self.write_log(q.get_nowait())
        self.w.after(100, self.check_q)
        
    def upd_set(self):
        b = self.en_var.get()
        j_in.enabled = b
        p_in.enabled = b
        
        j_in.mode = self.m1.get()
        p_in.mode = self.m2.get()
        if not b:
            j_in.release_all()
            p_in.release_all()
            
    def upd_dead(self, *a):
        off = int(float(self.dead_v.get()))
        j_in.min_val = 500 - off
        j_in.max_val = 500 + off

    def toggle(self):
        if self.running: self.close_it()
        else: self.start_it()

    def start_it(self):
        p = self.p_var.get()
        if not p: return
            
        try:
            self.ser = serial.Serial(p, 115200, timeout=1)
            self.running = True
            self.c_btn.config(text="Disconnect")
            self.s_lbl.config(text=f"Connected: {p}", foreground="green")
            self.write_log(f"Opened {p}")
            
            self.t = threading.Thread(target=self.loop, daemon=True)
            self.t.start()
        except Exception as ex:
            self.write_log(f"Error: {ex}")

    def close_it(self):
        self.running = False
        if self.ser and self.ser.is_open:
            self.ser.close()
        j_in.release_all()
        
        if self.btn_spc: kb.keyUp('space')
        if self.btn_shf: kb.keyUp('shift')
        if self.btn_f: kb.keyUp('f')
        self.btn_spc = self.btn_shf = self.btn_f = self.btn_esc = False
            
        self.c_btn.config(text="Connect")
        self.s_lbl.config(text="Not connected", foreground="red")
        self.write_log("Closed.")
        
    def loop(self):
        lut = 0
        while self.running and self.ser and self.ser.is_open:
            try:
                if self.ser.in_waiting > 150:
                    self.ser.reset_input_buffer()

                ln = self.ser.readline()
                if not ln: continue
                
                txt = ln.decode('utf-8', 'ignore').strip()
                if not txt: continue
                
                pts = txt.split(',')
                if len(pts) >= 8:
                    try:
                        # parse exactly like the standalone script
                        a1 = int(pts[1])
                        a2 = int(pts[2])
                        b1 = int(pts[4])
                        b2 = int(pts[5])
                        b3 = int(pts[6])
                        b4 = int(pts[7])
                        
                        low = 470
                        high = 560

                        # X axis
                        if a1 < low:
                            if not j_in.active.issuperset({'left'}): j_in.press('left')
                            j_in.release('right')
                        elif a1 > high:
                            if not j_in.active.issuperset({'right'}): j_in.press('right')
                            j_in.release('left')
                        else:
                            j_in.release('left')
                            j_in.release('right')

                        # Y axis
                        if a2 > high:
                            if not j_in.active.issuperset({'up'}): j_in.press('up')
                            j_in.release('down')
                        elif a2 < low:
                            if not j_in.active.issuperset({'down'}): j_in.press('down')
                            j_in.release('up')
                        else:
                            j_in.release('up')
                            j_in.release('down')
                        
                        # Buttons
                        if b1 == 1:
                            if not self.btn_spc: kb.keyDown("space"); self.btn_spc = True
                        else:
                            if self.btn_spc: kb.keyUp("space"); self.btn_spc = False

                        if b2 == 1:
                            if not self.btn_shf: kb.keyDown("shift"); self.btn_shf = True
                        else:
                            if self.btn_shf: kb.keyUp("shift"); self.btn_shf = False

                        if b3 == 1:
                            if not self.btn_f: kb.keyDown("f"); self.btn_f = True
                        else:
                            if self.btn_f: kb.keyUp("f"); self.btn_f = False

                        if b4 == 1:
                            if not self.btn_esc: kb.press("esc"); self.btn_esc = True
                        else:
                            self.btn_esc = False
                        
                        ct = time.time()
                        if ct - lut > 0.04:
                            self.w.after(0, self.upd_lbls, a1, a2)
                            lut = ct
                    except ValueError:
                        pass
                elif len(pts) == 2:
                    try:
                        xx = int(''.join(filter(str.isdigit, pts[0])))
                        yy = int(''.join(filter(str.isdigit, pts[1])))
                        j_in.update(xx, yy)
                        
                        ct = time.time()
                        if ct - lut > 0.04:
                            self.w.after(0, self.upd_lbls, xx, yy)
                            lut = ct
                    except:
                        pass
            except Exception as e:
                if self.running:
                    q.put(f"err: {e}")
                time.sleep(0.2)

    def upd_lbls(self, x, y):
        self.lx.config(text=f"X: {x}")
        self.ly.config(text=f"Y: {y}")

    def start_server(self):
        self.flask_t = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False), daemon=True)
        self.flask_t.start()
        
    def quit(self):
        self.close_it()
        self.w.destroy()

if __name__ == "__main__":
    r = tk.Tk()
    my_app = App(r)
    r.protocol("WM_DELETE_WINDOW", my_app.quit)
    r.mainloop()
