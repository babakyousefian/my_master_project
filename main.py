from fastapi import FastAPI, HTTPException, Request , Query
from pydantic import BaseModel
from typing import Optional, Dict, Any , List , Union
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse , FileResponse , HTMLResponse
from fastapi.staticfiles import StaticFiles

import threading
import multiprocessing
import time
import os
import random
import logging
from multiprocessing import Process, current_process
from datetime import datetime


# Third-party libs requested
import httpx
import aiohttp
import networkx as nx
from requests_oauthlib import OAuth2Session  # requests-oauthlib
import typer  # used to show a CLI-capable function (we will call it programmatically)
# pytest / pyinstaller / gunicorn are not imported in runtime here (they're dev/runtime tools)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")



# -----------------------------------------
# Config
# -----------------------------------------
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://babakyousefian.ir",
    "http://babakyousefian.ir",
    "https://www.babakyousefian.ir",
    "http://www.babakyousefian.ir",
    "*"
]

app = FastAPI(title="Thread and Process Based Parallelism API - Babak yousefian")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


# -----------------------------------------
# Request model
# -----------------------------------------

class ScenarioRequest(BaseModel):
    type: str
    scenario_task: int
    scenario_number: Optional[int] = 3

# -----------------------------------------
# Server-side explanations
# -----------------------------------------

SERVER_TASK_DESCRIPTIONS: Dict[str, Dict[int, str]] = {
    "thread": {
        1: """Thread Defining — تعریف/اجرای نخ‌ها و مقایسه‌ی start/join در سه سناریو
- هدف: مشاهده‌ی تفاوت زمان‌بندی و ترتیب لاگ‌ها وقتی نخ‌ها را به شکل‌های مختلف شروع/پایان می‌دهیم.
- پیاده‌سازی: ۱۰ نخ ساده که تابعی سبک (_t_my_func) را با یک اندیس اجرا می‌کنند.
- سناریو ۱: همه‌ی نخ‌ها را start می‌کنیم و سپس همه را join؛ حداکثر هم‌پوشانی اجرا.
- سناریو ۲: برای هر نخ بلافاصله پس از start، همان نخ را join می‌کنیم؛ عملاً شبه‌سریالی.
- سناریو ۳: همه‌ی نخ‌ها start می‌شوند و با یک حلقه‌ی انتظار (busy/poll) تا پایان همگی صبر می‌کنیم.
- نکته: ترتیب لاگ‌ها در سناریوی ۱ و ۳ پیش‌بینی‌پذیر نیست؛ به زمان‌بند OS وابسته است.
- خروجی: رشته‌های «my_func called…» برای هر اندیس، با ترتیب‌های متفاوت بسته به سناریو.
- نکته‌ی ایمنی: بدون join، ممکن است برنامه پیش از اتمام نخ‌ها خاتمه یابد.
- کاربرد: درک تفاوت الگوی «start-all/join-all» در برابر «start-then-join-per-thread».
- هشدار: کار CPU-bound با نخ‌ها به‌خاطر GIL سود زیادی نمی‌برد؛ I/O-bound مناسب‌تر است.""",

        2: """Thread Current — نام‌گذاری نخ‌ها و مدیریت شروع/پایان
- هدف: ردیابی چرخه‌ی عمر نخ‌ها با نام‌گذاری واضح و لاگ «starting/exiting».
- پیاده‌سازی: _t_function با خواب کوتاه و دو لاگ برای شروع/خاتمه.
- سناریو ۱: همه‌ی نخ‌ها را start و سپس join می‌کنیم؛ هم‌پوشانی و ترتیب پایان نامعین است.
- سناریو ۲: start سپس بلافاصله join برای هر نخ؛ ترتیب لاگ‌ها عمدتاً ترتیبی می‌شود.
- سناریو ۳: همه‌ی نخ‌ها start می‌شوند و با یک sleep کلی، تکمیل آن‌ها را غیرمستقیم انتظار می‌کشیم.
- نکته: نام‌گذاری نخ‌ها (Thread_A/B/C) دیباگ را به‌شدت ساده می‌کند.
- ابزار: می‌توان از thread.ident یا threading.current_thread().name برای تشخیص استفاده کرد.
- خروجی: دنباله‌ی «Thread_X --> starting» و سپس «… exiting» برحسب سناریو.
- کاربرد: پایش عملیات I/O موازی یا کارهای کوچک که نیاز به همروندی سبک دارند.
- هشدار: وابستگی به sleep به‌جای join ممکن است در بارهای متفاوت، نتایج ناپایدار بدهد.""",

        3: """Thread Subclass — ارث‌بری از threading.Thread و ثبت ترتیب اتمام
- هدف: سفارشی‌سازی رفتار نخ از طریق کلاس اختصاصی (MyThread) و ثبت زمان پایان.
- پیاده‌سازی: هر نخ delay متفاوت دارد؛ در سناریو ۳ پایان‌ها در completion_log ضبط می‌شود.
- سناریو ۱: start-all/join-all؛ همه پایان می‌یابند و لاگ ترتیب شروع/پایان ثبت می‌شود.
- سناریو 2: start سپس join برای هر نخ؛ عملاً اجرای ترتیبی و پایدارتر در خروجی.
- سناریو 3: start-all و جمع‌آوری ترتیب اتمام واقعی با time.time؛ سپس مرتب‌سازی.
- خروجی: «Thread#i running… / over» و فهرست مرتب‌شده‌ی پایان‌ها (sorted_log).
- نکته: subclass اجازه می‌دهد منابع را در __init__ تزریق و در run مصرف کنیم.
- کاربرد: زمانی که نیاز به state داخلی، hookهای سفارشی، یا متریک‌های زمان‌بندی داریم.
- هشدار: اشتراک state بین نخ‌ها بدون قفل می‌تواند وضعیت مسابقه ایجاد کند.
- نکته‌ی طراحی: از Queue برای ارسال/دریافت پیام امن بین نخ‌ها استفاده کنید.""",

        4: """Thread with Lock — حفاظت از بخش بحرانی با Lock
- هدف: جلوگیری از تداخل دسترسی همزمان به منبع مشترک (مثلاً لیست خروجی).
- پیاده‌سازی: در تابع کارگر، با with lock: بخش بحرانی را اتمیک می‌کنیم.
- سناریو ۱: start-all/join-all؛ قفل تضمین می‌کند لاگ‌های هر کارگر به‌صورت هم‌پیوسته ثبت شوند.
- سناریو ۲: start سپس join برای هر نخ؛ به‌طور طبیعی تداخل کمتر رخ می‌دهد.
- سناریو ۳: start-all و انتظار فعال تا پایان؛ همچنان به قفل برای اطمینان نیاز است.
- خروجی: پیام‌های «running/over» با ترتیب قابل‌قبول و بدون مخلوط شدن نیمه‌گزارش‌ها.
- نکته: Lock ساده است و برای جلوگیری از race condition ضروری می‌باشد.
- هشدار: از قفل‌های تودرتو اجتناب کنید؛ بن‌بست محتمل می‌شود.
- مقایسه: برای ورودهای چندباره‌ی همان نخ از RLock استفاده کنید (قفل بازگشتی).
- کاربرد: نوشتن در فایل مشترک، شمارنده‌ی مشترک، یا ساختار داده‌ی مشترک.""",

        5: """Thread with RLock — قفل بازگشتی برای الگوی افزودن/حذف
- هدف: اجازه‌ی ورود تودرتوی همان نخ به بخش بحرانی (re-entrant) بدون بن‌بست.
- پیاده‌سازی: دو کارگر افزاینده/کاهنده روی ساختارهای داده کار می‌کنند و RLock حفاظت می‌کند.
- سناریو ۱: افزودن و حذف همزمان؛ توازن و درستی داده با قفل بازگشتی حفظ می‌شود.
- سناریو ۲: ابتدا افزودن‌ها کامل، سپس حذف؛ خروجی پایدارتر و قابل پیش‌بینی‌تر.
- سناریو ۳: هر دو همزمان با انتظار فعال تا اتمام؛ سناریوی واقعی‌تر با تداخل محتمل.
- خروجی: پیام‌های «ADDED…» و «REMOVED…» که وضعیت صف/لیست را نشان می‌دهند.
- نکته: RLock وقتی مفید است که توابع قفل‌شده توابع قفل‌شده‌ی دیگری را فراخوانی کنند.
- هشدار: استفاده‌ی بی‌مورد از RLock پیچیدگی می‌آورد؛ اولویت با طراحی ساده است.
- جایگزین: برای تولیدکننده/مصرف‌کننده، Queue اغلب امن‌تر و ساده‌تر از قفل است.
- کاربرد: APIهایی با لایه‌های چندگانه که همگی نیاز به حفاظت دارند.""",

        6: """Thread with Semaphore — تولیدکننده/مصرف‌کننده با سمافور
- هدف: کنترل ظرفیت/سیگنال‌دهی بین تولیدکننده‌ها و مصرف‌کننده‌ها با شمارنده‌ی سمافور.
- پیاده‌سازی: sem با مقدار اولیه ۰؛ تولیدکننده release و مصرف‌کننده acquire می‌کند.
- سناریو ۱: ترتیب start مشترک برای همه؛ مصرف‌کننده‌ها ابتدا منتظر می‌مانند تا آیتم برسد.
- سناریو ۲: تولید و مصرف به‌صورت جفت start/join؛ رفتار تقریباً ترتیبی و پایدار.
- سناریو ۳: start-all با هم و join کلی؛ بیشترین هم‌پوشانی و تداخل زمانی.
- خروجی: «Consumer is waiting» → پس از release ها «Consumer notify…».
- نکته: سمافور برای کنترل ظرفیت منابع محدود (اتصالات، مجوزها) مناسب است.
- هشدار: مراقب «گم‌شدن سیگنال» در طراحی‌های پیچیده باشید؛ از صف‌ها برای داده استفاده کنید.
- مقایسه: Lock برای انحصار، Semaphore برای شمارش/ظرفیت، Event برای سیگنال تک‌حالته.""",

        7: """Thread with Barrier — همگام‌سازی نخ‌ها روی یک نقطه‌ی مشترک
- هدف: تضمین این‌که چند نخ تا رسیدن همه به «نقطه‌ی سد» جلوتر نروند.
- پیاده‌سازی: Barrier(3) و یک Event برای شروع مشابه «مسابقه» (START RACE).
- سناریو ۱: نخ‌ها start شده و با تاخیر آزادسازی، همگی تقریباً همزمان از سد عبور می‌کنند.
- سناریو ۲: تاخیر کمتر؛ همچنان همه باید به سد برسند تا عبور کنند؛ ترتیب عبور نزدیک به هم است.
- سناریو ۳: شروع‌های پله‌ای و سپس آزادسازی؛ مشاهده‌ی اثر زمان رسیدن متفاوت به سد.
- خروجی: زمان «reached the barrier» برای هر نخ و «Race over!» در پایان.
- نکته: Barrier برای الگوریتم‌های فازبندی‌شده (مرحله‌به‌مرحله) بسیار مفید است.
- هشدار: اگر یکی از نخ‌ها هرگز نرسد، دیگران در انتظار می‌مانند یا BrokenBarrierError رخ می‌دهد.
- مقایسه: Event برای یک‌سویه‌کردن شروع/ایست مفید است؛ Barrier برای هم‌زمانی نقطه‌ای.""",
    },

    "process": {
        1: """Process Spawn — ایجاد چند پردازه و مقایسه‌ی start/join
- هدف: مشاهده‌ی رفتار پردازه‌ها (حافظه‌ی مستقل، زمان‌بندی OS، هزینه‌ی ایجاد).
- پیاده‌سازی: چند Process که تابع سبک (_p_my_func) را با اندیس اجرا و روی Manager.list خروجی می‌نویسند.
- سناریو ۱: start-all سپس join-all؛ بیشترین هم‌پوشانی پردازه‌ها.
- سناریو ۲: start سپس join برای هر پردازه؛ رفتار ترتیبی و قابل پیش‌بینی.
- سناریو ۳: start-all و سپس join-all پس از تکمیل؛ مشابه ۱ با تفاوت زمان‌بندی.
- خروجی: «output from myFunc…» برای هر مقدار و لاگ «calling myFunc…».
- نکته: هر پردازه فضای آدرس جداگانه دارد؛ state مشترک مستقیم وجود ندارد.
- ابزار اشتراک: Manager.list/Queue برای تبادل امن داده بین پردازه‌ها.
- هشدار: ایجاد پردازه نسبت به نخ پرهزینه‌تر است؛ برای CPU-bound ارزشمند است.
- کاربرد: کارهای سنگین ریاضی/علمی که از چند هسته بهره می‌برند.""",

        2: """Process Naming — نام‌گذاری پردازه‌ها و current_process().name
- هدف: بهبود قابلیت مشاهده و دیباگ با نام‌های معنادار برای پردازه‌ها.
- پیاده‌سازی: تنظیم name در سازنده‌ی Process و لاگ «Starting/Exiting process name = …».
- سناریو ۱: ترکیب یک پردازه‌ی نام‌دار و یک پردازه‌ی بی‌نام؛ مشاهده‌ی تفاوت لاگ‌ها.
- سناریو ۲: اجرای ترتیبی پردازه‌ها با/بی‌نام برای خروجی پایدارتر.
- سناریو ۳: start-all/join-all با چند پردازه‌ی نام‌دار/بی‌نام برای تداخل زمانی.
- خروجی: نشان می‌دهد current_process().name چگونه در لاگ‌ها ظاهر می‌شود.
- نکته: نام‌گذاری به ردیابی مشکلات و این‌که کدام وظیفه در کدام پردازه است کمک می‌کند.
- کاربرد: سامانه‌های چندپردازه‌ای با نقش‌های متفاوت (worker, io, cpu).
- هشدار: به‌خاطر جدایی حافظه، لاگ مشترک را با Queue یا logging handlers هماهنگ کنید.
- نکته‌ی دیباگ: pid (os.getpid()) را با نام ترکیب کنید تا یکتا باشد.""",

        3: """Process Background — تفاوت daemon و non-daemon هنگام خروج برنامه
- هدف: درک رفتار پردازه‌های daemon که با پایان پردازه‌ی والد قطع می‌شوند.
- پیاده‌سازی: دو تابع: «NO_background» (غیر دیمون) و «background» (دیمون).
- سناریو ۱: تنها غیر دیمون؛ همیشه کامل می‌شود و خروجی کامل تولید می‌کند.
- سناریو ۲: غیر دیمون + دیمون؛ ممکن است دیمون با پایان والد زودتر قطع شود.
- سناریو ۳: مشابه ۲ با زمان‌بندی متفاوت؛ مشاهده‌ی تفاوت‌های ظریف زمان‌بندی.
- خروجی: لاگ‌های «Starting…/Exiting…» برای هر کدام و مقادیر شمارش شده.
- هشدار: پردازه‌ی daemon اجازه‌ی ایجاد فرزند جدید را ندارد و ممکن است ناگهانی متوقف شود.
- کاربرد: کارهای پس‌زمینه‌ی غیرحیاتی که قطع ناگهانی قابل‌قبول است.
- توصیه: برای خاموشی تمیز، از Event/Queue و الگوی «graceful shutdown» استفاده کنید.""",

        4: """Process Kill — terminate()/exitcode و چرخه‌ی حیات پردازه
- هدف: نشان دادن وضعیت‌های قبل/حین/پس از اجرا و خاتمه‌ی اجباری پردازه‌ها.
- پیاده‌سازی: کارگر طولانی (_p_long_worker) + لاگ وضعیت با _p_print_status.
- سناریو ۱: چند پردازه را start کرده، سپس terminate، سپس join و ثبت exitcode.
- سناریو ۲: ایجاد/خاتمه‌ی ترتیبی پردازه‌ها برای مشاهده‌ی دقیق‌تر انتقال وضعیت.
- سناریو ۳: start-all، terminate-all، سپس join-all و گزارش نهایی.
- خروجی: خطوط «Process before execution/running/terminated/joined» و کد خروج.
- هشدار: terminate خشن است؛ ممکن است منابع آزاد نشوند یا داده نیمه‌نوشته بماند.
- توصیه: در تولید، سیگنال نرم (Event/Queue) و زمان‌بندی تایم‌اوت را ترجیح دهید.
- نکته‌ی پرتابل: رفتار terminate در سیستم‌عامل‌ها اندکی متفاوت است.""",

        5: """Process Subclass — ارث‌بری از multiprocessing.Process و متد run
- هدف: کپسوله‌سازی منطق پردازه در یک کلاس (MyProcess) با state داخلی تمیز.
- پیاده‌سازی: override متد run و استفاده از نام پردازه برای لاگ معنادار.
- سناریو ۱: start-all/join-all برای چند نمونه و لاگ وضعیت قبل/حین/پس از اجرا.
- سناریو ۲: اجرای ترتیبی چند نمونه برای خروجی پایدارتر و قابل‌پیش‌بینی.
- سناریو ۳: ترکیبی با تعداد بیش‌تر و لاگ «finished» برای هر پردازه.
- خروجی: «called run method by …» و وضعیت‌های is_alive در نقاط کلیدی.
- کاربرد: معماری شی‌ءگرا برای workerها، تزریق وابستگی و تست‌پذیری بهتر.
- نکته: پارامتر name در سازنده، لاگ و مانیتورینگ را ساده می‌کند.
- هشدار: اشیای ناهمگام/ناانتقال‌پذیر را بین پردازه‌ها به‌طور مستقیم به اشتراک نگذارید.""",

        6: """Process Queue — تولیدکننده/مصرف‌کننده بین پردازه‌ها با Queue و Event
- هدف: تبادل داده‌ی ایمن بین پردازه‌ها (IPC) بدون نیاز به قفل دستی.
- پیاده‌سازی: تولیدکننده آیتم‌ها را put کرده و پس از پایان، Event را set می‌کند؛ مصرف‌کننده تا تهی‌شدن و set شدن منتظر می‌ماند.
- سناریو ۱: تولید و مصرف همزمان؛ بیشترین هم‌پوشانی و throughput.
- سناریو ۲: ابتدا تولید کامل، سپس مصرف؛ ترتیب پایدار اما هم‌پوشانی کمتر.
- سناریو ۳: مشابه ۱ با انتظار تا اتمام هر دو؛ تضمین تخلیه‌ی کامل صف.
- خروجی: «Producer : item X appended… / Consumer : item X popped…» و اندازه‌ی صف.
- نکته: q.qsize روی برخی پلتفرم‌ها دقیق نیست؛ برای منطق کنترلی به آن تکیه نکنید.
- توصیه: برای پایان تمیز، از sentinels (None) یا Event استفاده کنید.
- هشدار: هرگز اشیای غیرقابل pickling را در صف قرار ندهید؛ شکست انتقال رخ می‌دهد.""",

        7: """Process Barrier — همگام‌سازی بین پردازه‌ها با Barrier و مدیریت timeout
- هدف: اطمینان از این‌که همه‌ی پردازه‌ها به نقطه‌ی سد برسند سپس با هم عبور کنند.
- پیاده‌سازی: multiprocessing.Barrier(3) و کارگرهایی که زمان رسیدن را لاگ می‌کنند.
- سناریو ۱: سه پردازه همزمان به سد رسیده و سپس با هم آزاد می‌شوند.
- سناریو ۲: اجرای ترتیبی پردازه‌ها (start/join) که منجر به timeout و شکست سد می‌شود.
- سناریو ۳: start-all و سپس join-all؛ رفتار مشابه سناریوی ۱ با تغییرات زمانی جزئی.
- خروجی: «waiting at barrier / passed barrier» یا پیام شکست با Exception.
- نکته: تعداد parties باید دقیقاً با Barrier منطبق باشد؛ در غیر این صورت آزاد نمی‌شود.
- هشدار: BrokenBarrierError را مدیریت کنید تا بن‌بست رخ ندهد.
- کاربرد: الگوریتم‌های مرحله‌ای (مرحله ۱ همه، سپس مرحله ۲ همه، …).""",

        8: """Process Pool — اجرای map/apply و استفاده‌ی بهتر از CPU
- هدف: مدیریت گروهی از workerها برای توزیع خودکار کار (map/apply).
- پیاده‌سازی: map روی بازه‌ای از اعداد، apply برای فراخوانی تک، و اجرای چند Process ساده.
- سناریو ۱: Pool(4).map روی ۳۲ عدد؛ پردازش موازی و جمع‌آوری نتایج در لیست.
- سناریو ۲: Pool(1).apply برای سه مقدار؛ نشان دادن semantics فراخوانی همگام.
- سناریو ۳: اجرای سه Process مستقل (خارج از Pool) برای مقایسه‌ی لاگ و نتایج.
- خروجی: «Pool : [نتایج]» و لاگ نام پردازه‌ها/زمان اجرا برای کارگران.
- نکته: برای کارهای بسیار کوچک، سربار pickling/IPC می‌تواند سود را کم کند.
- توصیه: از with Pool(...) استفاده کنید تا بستن تمیز و join خودکار انجام شود.
- هشدار (ویندوز): همیشه محافظ if __name__ == \"__main__\" را رعایت کنید تا فرایندها درست اسپان شوند.""",
    },
}


# -----------------------------------------
# Thread Scenario
# -----------------------------------------



def my_func(index: int, output: list):
    output.append(f"[{index}] my_func called by thread N°{index}")

def thread_defining_scenarios():
    results = {"scenario 1": [], "scenario 2": [], "scenario 3": []}

    threads = []
    for i in range(10):
        t = threading.Thread(target=my_func, args=(i, results["scenario 1"]))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

    for i in range(10):
        t = threading.Thread(target=my_func, args=(i, results["scenario 2"]))
        threads.append(t)
        t.start()
        t.join()

    threads = []
    for i in range(10):
        t = threading.Thread(target=my_func, args=(i, results["scenario 3"]))
        threads.append(t)
        t.start()

    while any(t.is_alive() for t in threads):
        time.sleep(0.1)

    return results



def function(name , output:list=[]):
    output.append(f"{name} --> starting")
    time.sleep(0.2)
    output.append(f"{name} --> exiting")

def thread_current_scenarios():
    results = {"scenario 1":[] , "scenario 2":[] , "scenario 3":[]}
    names = ["A", "B", "C"]
    thread = []
    threads = [threading.Thread(target=function, args=(f"Thread_{n}",results["scenario 1"])) for n in names]
    for t in threads:
        thread.append(t)
        t.start()
    for t in threads:
        t.join()

    thread = []
    for n in names:
        t = threading.Thread(target=function, args=(f"Thread_{n}",results["scenario 2"]))
        thread.append(t)
        t.start()
        t.join()

    thread = []
    threads = [(n, threading.Thread(target=function, args=(f"Thread_{n}",results["scenario 3"]))) for n in names]
    for _, t in threads:
        thread.append(t)
        t.start()
    time.sleep(1)

    return results


class MyThread(threading.Thread):
    def __init__(self, name, delay, completion_log , output):
        super().__init__()
        self.name = name
        self.delay = delay
        self.completion_log = completion_log
        self.output = output

    def run(self):
        self.output.append(f"---> {self.name} running, belonging to process ID {os.getpid()}")
        time.sleep(self.delay)
        end_time = time.time()
        self.output.append(f"---> {self.name} over")
        self.completion_log.append((end_time, self.name))



def thread_subclass_scenarios():
    """
    FIXED: returns under 'results' (no trailing spaces) so filter_result_by_scenario()
    can keep ONLY the selected scenario (1..3) from the client request.
    """
    start_ts = time.time()

    results = {"scenario 1": [], "scenario 2": [], "scenario 3": []}
    delays = [0.9, 0.5, 0.8]

    # Scenario 1: start-all, then join-all
    threads = [MyThread(f"Thread#{i}", delays[i % 3], [], results["scenario 1"]) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Scenario 2: start then join per thread (sequential-ish)
    for i in range(10):
        t = MyThread(f"Thread#{i}", delays[i % 3], [], results["scenario 2"])
        t.start()
        t.join()

    # Scenario 3: start-all and collect real completion order
    completion_log = []
    threads = [MyThread(f"Thread#{i}", delays[i % 3], completion_log, results["scenario 3"]) for i in range(10)]
    for t in threads:
        t.start()
    # wait until all have appended to completion_log
    while len(completion_log) < 10:
        time.sleep(0.01)
    # record the completion order inside scenario 3 itself (no top-level 'sorted_log')
    sorted_log = sorted(completion_log, key=lambda x: x[0])
    results["scenario 3"].append("Completion order:")
    results["scenario 3"].extend([f"{name} finished at {end:.4f}" for end, name in sorted_log])

    return {
        "results": results,
        "timer": f"--- {time.time() - start_ts:.3f} seconds ---"
    }



def locked_function(name , lock , output:list=[]):
    with lock:
        output.append(f"{name} running, belonging to process ID {os.getpid()}")
        time.sleep(1)
        output.append(f"{name} over")



def thread_with_lock_scenarios():
    """
    FIXED: returns under 'results' (no trailing spaces) so the selected scenario (1..3)
    is shown alone after filtering.
    """
    start_ts = time.time()
    results = {"scenario 1": [], "scenario 2": [], "scenario 3": []}
    lock = threading.Lock()

    def _locked_function(name, out_list):
        with lock:
            out_list.append(f"{name} running, belonging to process ID {os.getpid()}")
            time.sleep(1)
            out_list.append(f"{name} over")

    # Scenario 1: start-all then join-all
    threads = [threading.Thread(target=_locked_function, args=(f"Thread#{i}", results["scenario 1"])) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Scenario 2: start then join per thread (sequential)
    for i in range(10):
        t = threading.Thread(target=_locked_function, args=(f"Thread#{i}", results["scenario 2"]))
        t.start()
        t.join()

    # Scenario 3: start-all, then poll is_alive() (no immediate joins)
    threads = [(i, threading.Thread(target=_locked_function, args=(f"Thread#{i}", results["scenario 3"]))) for i in range(10)]
    for _, t in threads:
        t.start()
    while any(t.is_alive() for _, t in threads):
        time.sleep(0.1)

    return {
        "results": results,
        "status": "END.",
        "timer": f"--- {time.time() - start_ts:.3f} seconds ---"
    }



def setup_data():
    return list(range(16)), [1]


def add_items(rlock , to_add , output:list=[]):
    while to_add:
        with rlock:
            item = to_add.pop(0)
            output.append(f"ADDED one item -->{len(to_add)} item to ADD")
            time.sleep(0.1)


def remove_items(rlock , to_remove , output:list=[]):
    while to_remove:
        with rlock:
            item = to_remove.pop()
            output.append(f"REMOVED one item -->{len(to_remove)} item to REMOVE")
            time.sleep(0.15)


def thread_with_rlock_scenarios():

    results = {"scenario 1":[] , "scenario 2":[] , "scenario 3":[]}

    rlock = threading.RLock()

    to_add, to_remove = setup_data()

    t1 = threading.Thread(target=add_items , args=(rlock , to_add , results["scenario 1"]))
    t2 = threading.Thread(target=remove_items , args=(rlock , to_remove , results["scenario 1"]))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    to_add, to_remove = setup_data()

    t1 = threading.Thread(target=add_items , args=(rlock , to_add , results["scenario 2"]))
    t1.start()
    t1.join()

    t2 = threading.Thread(target=remove_items , args=(rlock , to_remove , results["scenario 2"]))
    t2.start()
    t2.join()

    to_add, to_remove = setup_data()

    t1 = threading.Thread(target=add_items , args=(rlock , to_add , results["scenario 3"]))
    t2 = threading.Thread(target=remove_items , args=(rlock , to_remove , results["scenario 3"]))
    t1.start()
    t2.start()


    while t1.is_alive() or t2.is_alive():
        time.sleep(0.05)

    return results




def producer(sem: threading.Semaphore, id_: int , output:list=[]):
    time.sleep(2)
    logging.info(f"Producer notify: item number {id_}")
    output.append(f"Producer notify: item number {id_}")
    sem.release()

def consumer(sem: threading.Semaphore , output:list=[]):
    logging.info("Consumer is waiting")
    output.append("Consumer is waiting")
    sem.acquire()
    logging.info("Consumer notify: got the item")
    output.append("Consumer notify: got the item")

def scenario(label: int , output:list=[]):
    logging.info(f"--- thread_with_semaphore: Scenario {label} ---")

    output.append(f"--- thread_with_semaphore: Scenario {label} ---")

    sem = threading.Semaphore(0)
    producers = [threading.Thread(target=producer, args=(sem, 100 + i , output)) for i in range(5)]
    consumers = [threading.Thread(target=consumer, args=(sem, output)) for _ in range(5)]

    if label == 1:
        for t in consumers + producers:
            output.append(f"{t}")
            t.start()
        for t in consumers + producers:
            t.join()

    elif label == 2:
        for p, c in zip(producers, consumers):
            p.start()
            p.join()
            c.start()
            c.join()
            output.append(f"{p}")
            output.append(f"{c}")

    elif label == 3:
        for t in consumers + producers:
            t.start()
            output.append(f"{t}")
    time.sleep(7)

def thread_with_semaphore_scenarios():

    results = {"scenario 1":[] , "scenario 2":[] , "scenario 3":[]}

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(threadName)s] %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")


    scenario1_list = []
    scenario(1 , scenario1_list)
    scenario2_list = []
    scenario(2 , scenario2_list)
    scenario3_list = []
    scenario(3 , scenario3_list)

    results["scenario 1"].append(scenario1_list)
    results["scenario 2"].append(scenario2_list)
    results["scenario 3"].append(scenario3_list)

    return results



def run_barrier(name, barrier, starter_event=None , output:list=[]):
    if starter_event:
        starter_event.wait()
    output.append(f"{name} reached the barrier at: {time.ctime()}")
    barrier.wait()

def thread_with_barrier_scenarios():

    results = {"scenario 1":[] , "scenario 2":[] , "scenario 3":[]}

    myList = ["Dewey", "Huey", "Louie"]

    results["scenario 1"].clear()
    results["scenario 1"].append("START RACE!!!!")
    thread = []
    barrier1 = threading.Barrier(3)
    starter_event2 = threading.Event()
    threads1 = [threading.Thread(target=run_barrier, args=(name, barrier1 , starter_event2 , results["scenario 1"])) for name in myList]
    for t in threads1:
        thread.append(t)
        t.start()
        time.sleep(1)
        starter_event2.set()
    for t in threads1:
        t.join()
    results["scenario 1"].append("Race over!")

    results["scenario 2"].clear()
    results["scenario 2"].append("START RACE!!!!")
    barrier2 = threading.Barrier(3)
    starter_event = threading.Event()
    threads2 = []

    for name in myList:
        t = threading.Thread(target=run_barrier, args=(name, barrier2, starter_event , results["scenario 2"]))
        threads2.append(t)
        t.start()

    time.sleep(0.5)
    starter_event.set()

    for t in threads2:
        t.join()
    results["scenario 2"].append("Race over!")

    results["scenario 3"].clear()
    results["scenario 3"].append("START RACE!!!!")
    barrier3 = threading.Barrier(3)
    starter_event3 = threading.Event()
    threads3 = [threading.Thread(target=run_barrier, args=(name, barrier3 , starter_event3 , results["scenario 3"])) for name in myList]
    for t in threads3:
        t.start()
        time.sleep(1)
        starter_event3.set()
    time.sleep(2)
    results["scenario 3"].append("Race over!")

    return results



def myFunc(n, output):
    output.append(f"calling myFunc from process n°: {n}")
    for i in range(n + 1):
        output.append(f"output from myFunc is :{i}")
        time.sleep(0.5)

def process_spawn_scenarios():
    final_output = []
    manager = multiprocessing.Manager()

    final_output.append("process_spawn_scenarios...\n")
    final_output.append("--- process_spawn: Scenario 1 ---")
    output1 = manager.list()
    procs1 = [multiprocessing.Process(target=myFunc, args=(i, output1)) for i in range(6)]
    for p in procs1:
        p.start()
        time.sleep(1)
    for p in procs1:
        p.join()
    final_output.extend(list(output1))

    final_output.append("\n--- process_spawn: Scenario 2 ---")
    output2 = manager.list()
    for i in range(6):
        p = multiprocessing.Process(target=myFunc, args=(i, output2))
        p.start()
        p.join()
    final_output.extend(list(output2))

    final_output.append("\n--- process_spawn: Scenario 3 ---")
    output3 = manager.list()
    procs3 = [multiprocessing.Process(target=myFunc, args=(i, output3)) for i in range(6)]
    for p in procs3:
        p.start()
    time.sleep(6)
    final_output.extend(list(output3))

    return {
        "scenario1 ":list(output1),
        "scenario2 ":list(output2),
        "scenario3 ":list(output3)
    }



def named_worker(output):
    name = multiprocessing.current_process().name
    output.append(f"Starting process name = {name}")
    time.sleep(0.2)
    output.append(f"Exiting process name = {name}")

def process_naming_scenarios():
    manager1 = multiprocessing.Manager()
    output1 = manager1.list()
    output1.append("\n\n process_naming_scenarios... \n\n")

    output1.append("\n--- process_naming: Scenario 1 ---")
    p1 = multiprocessing.Process(target=named_worker, name="myFunc process" , args=(output1, ))
    p2 = multiprocessing.Process(target=named_worker , args=(output1, ))

    p1.start()
    p2.start()

    p1.join()
    p2.join()

    output2 = manager1.list()
    output2.append("\n--- process_naming: Scenario 2 ---")
    for i in range(2):
        name = "myFunc process" if i == 0 else None
        p = multiprocessing.Process(target=named_worker, name=name , args=(output2, ))
        p.start()
        p.join()


    output3 = manager1.list()
    output3.append("\n--- process_naming: Scenario 3 ---")
    procs = [
        multiprocessing.Process(target=named_worker, name="myFunc process" , args=(output3, )),
        multiprocessing.Process(target=named_worker , args=(output3, ))
    ]
    for p in procs:
        p.start()

    time.sleep(1)
    return {
        "scenario1 ":list(output1),
        "scenario2 ":list(output2),
        "scenario3 ":list(output3)
    }


def background_process(output , iteration):
    output.append("Starting background_process")
    for i in range(iteration):
        if i % 2 != 0:
            output.append(f"---> {i}")
            time.sleep(0.5)
    output.append("Exiting background_process")

def no_background_process(output , iteration):
    output.append("Starting NO_background_process")
    for i in range(iteration):
        if i % 2 == 0:
            output.append(f"---> {i}")
            time.sleep(0.5)
    output.append("Exiting NO_background_process")

def process_background_scenarios():
    manager = multiprocessing.Manager()
    iteration = 10

    output1 = manager.list()
    output1.append("\n\n process_background_scenarios... \n\n")
    output1.append("\n--- process_background: Scenario 1 ---")
    p1 = multiprocessing.Process(target=no_background_process, args=(output1, iteration))
    p1.start()
    p1.join()


    output2 = manager.list()
    output2.append("\n--- process_background: Scenario 2 ---")
    p2 = multiprocessing.Process(target=no_background_process, args=(output2, iteration))
    p3 = multiprocessing.Process(target=background_process, args=(output2, iteration), daemon=True)
    p2.start()
    p3.start()
    p2.join()
    p3.join()


    output3 = manager.list()
    output3.append("\n--- process_background: Scenario 3 ---")
    p4 = multiprocessing.Process(target=no_background_process, args=(output3, iteration))
    p5 = multiprocessing.Process(target=background_process, args=(output3, iteration), daemon=True)
    p4.start()
    p5.start()
    while p4.is_alive() or p5.is_alive():
        time.sleep(0.5)

    return {
        "scenario1": list(output1),
        "scenario2": list(output2),
        "scenario3": list(output3)
    }

def long_worker(output):
    output.append(f"{os.getpid()} is running...")
    time.sleep(2)

def print_status(stage, proc , output):
    output.append(f"{stage}: {proc} {proc.is_alive()}")

def process_kill_scenarios():
    myManager = multiprocessing.Manager()
    output1 = myManager.list()
    output1.append("\n\n process_kill_scenarios... \n\n")

    output1.append("\n--- process_kill: Scenario 1 ---")
    procs = [multiprocessing.Process(target=long_worker , args=(output1, )) for _ in range(3)]
    for p in procs:
        print_status("Process before execution", p , output1)
        p.start()
        print_status("Process running", p , output1)

    time.sleep(0.5)
    for p in procs:
        p.terminate()
        print_status("Process terminated", p , output1)
        p.join()
        print_status("Process joined", p , output1)
        output1.append(f"Process exit code: {p.exitcode}")


    output2 = myManager.list()
    output2.append("\n--- process_kill: Scenario 2 ---")
    for _ in range(3):
        p = multiprocessing.Process(target=long_worker , args=(output2, ))
        print_status("Process before execution", p , output2)
        p.start()
        print_status("Process running", p , output2)

        time.sleep(0.5)
        p.terminate()
        print_status("Process terminated", p , output2)

        p.join()
        print_status("Process joined", p , output2)
        output2.append(f"Process exit code: {p.exitcode}")


    output3 = myManager.list()
    output3.append("\n--- process_kill: Scenario 3 ---")
    procs = [(i, multiprocessing.Process(target=long_worker , args=(output3, ))) for i in range(3)]
    for i, p in procs:
        print_status("Process before execution", p , output3)
        p.start()
        print_status("Process running", p , output3)

    time.sleep(0.5)
    for i, p in procs:
        p.terminate()
        print_status("Process terminated", p , output3)


        while p.is_alive():
            time.sleep(0.1)

        print_status("Process joined", p , output3)
        output3.append(f"Process exit code: {p.exitcode}")

        return {
            "scenario1 ":list(output1),
            "scenario2 ":list(output2),
            "scenario3 ":list(output3)
        }


class MyProcess(multiprocessing.Process):
    def __init__(self, proc_name, output):
        super().__init__(name=proc_name)
        self.output = output

    def run(self):
        self.output.append(f"called run method by {self.name}")
        time.sleep(0.3)


def process_subclass_scenarios():
    myManager = multiprocessing.Manager()

    output1 = myManager.list()
    output1.append("\n\n process_subclass_scenarios... \n\n")
    output1.append("\n--- process_subclass: Scenario 1 ---\n")
    procs1 = [MyProcess(f"MyProcess-{i + 1}", output1) for i in range(3)]
    for p in procs1:
        output1.append(f"Process before execution: {p.name} {p.is_alive()}")
        p.start()
        output1.append(f"Process running: {p.name} {p.is_alive()}")
    for p in procs1:
        p.join()
        output1.append(f"Process joined: {p.name} {p.is_alive()}")


    output2 = myManager.list()
    output2.append("\n--- process_subclass: Scenario 2 ---\n")
    for i in range(3, 6):
        p = MyProcess(f"MyProcess-{i + 1}", output2)
        output2.append(f"Process before execution: {p.name} {p.is_alive()}")
        p.start()
        output2.append(f"Process running: {p.name} {p.is_alive()}")
        p.join()
        output2.append(f"Process joined: {p.name} {p.is_alive()}")

    output3 = myManager.list()
    output3.append("\n--- process_subclass: Scenario 3 ---\n")
    procs3 = [MyProcess(f"MyProcess-{i + 1}", output3) for i in range(6, 10)]
    for p in procs3:
        output3.append(f"Process before execution: {p.name} {p.is_alive()}")
        p.start()
        output3.append(f"Process running: {p.name} {p.is_alive()}")


    while any(p.is_alive() for p in procs3):
        time.sleep(0.1)
    for p in procs3:
        output3.append(f"Process finished: {p.name} {p.is_alive()}")

    return {
        "scenario1": list(output1),
        "scenario2": list(output2),
        "scenario3": list(output3)
    }


def producer(q, finished_event , output , iteration):
    for _ in range(iteration):
        item = random.randint(1, 250)
        q.put(item)
        output.append(f"Process Producer : item {item} appended to queue producer-1")
        output.append(f"The size of queue is {q.qsize()}")
        time.sleep(0.2)
    finished_event.set()


def consumer(q, finished_event , output):
    time.sleep(0.5)
    while not q.empty() or not finished_event.is_set():
        if not q.empty():
            item = q.get()
            output.append(f"Process Consumer : item {item} popped from by consumer-2")
        time.sleep(0.3)
    output.append("the queue is empty")


def process_queue_scenarios():
    iteration = 10
    myManager = multiprocessing.Manager()
    output1 = myManager.list()
    output1.append("\n\n process_queue_scenarios...\n\n")


    output1.append("\n--- process_queue: Scenario 1 ---")
    q = multiprocessing.Queue()
    finished = multiprocessing.Event()
    p1 = multiprocessing.Process(target=producer, args=(q, finished , output1 , iteration))
    p2 = multiprocessing.Process(target=consumer, args=(q, finished , output1))
    p1.start()
    p2.start()
    p1.join()
    p2.join()


    output2 = myManager.list()
    output2.append("\n--- process_queue: Scenario 2 ---")
    q = multiprocessing.Queue()
    finished = multiprocessing.Event()
    p1 = multiprocessing.Process(target=producer, args=(q, finished , output2 , iteration))
    p1.start()
    p1.join()

    p2 = multiprocessing.Process(target=consumer, args=(q, finished , output2))
    p2.start()
    p2.join()


    output3 = myManager.list()
    output3.append("\n--- process_queue: Scenario 3 ---")
    q = multiprocessing.Queue()
    finished = multiprocessing.Event()
    p1 = multiprocessing.Process(target=producer, args=(q, finished , output3 , iteration))
    p2 = multiprocessing.Process(target=consumer, args=(q, finished , output3))
    p1.start()
    p2.start()

    while p1.is_alive() or p2.is_alive():
        time.sleep(0.8)


    return {
        "scenario1 ":list(output1),
        "scenario2 ":list(output2),
        "scenario3 ":list(output3)
    }


def barrier_worker(b, name , output):
    output.append(f"process {name} - waiting at barrier ----> {datetime.now()}")
    try:
        b.wait(timeout=5)
        output.append(f"process {name} - passed barrier ----> {datetime.now()}")
    except Exception as e:
        output.append(f"process {name} - barrier failed ({str(e)}) ----> {datetime.now()}")

def process_sync_barrier_scenarios():
    myManager = multiprocessing.Manager()
    output1 = myManager.list()
    output1.append("\n--- process_sync_barrier: Scenario 1 ---")
    b1 = multiprocessing.Barrier(3)
    procs1 = [multiprocessing.Process(target=barrier_worker, args=(b1, f"p{i+1}" , output1)) for i in range(3)]
    for p in procs1:
        p.start()
    for p in procs1:
        p.join()

    output2 = myManager.list()
    output2.append("\n--- process_sync_barrier: Scenario 2 ---")
    b2 = multiprocessing.Barrier(3)
    for i in range(3):
        p = multiprocessing.Process(target=barrier_worker, args=(b2, f"p{i+1}" , output2))
        p.start()
        p.join()

    output3 = myManager.list()
    output3.append("\n--- process_sync_barrier: Scenario 3 ---")
    b3 = multiprocessing.Barrier(3)
    procs3 = [multiprocessing.Process(target=barrier_worker, args=(b3, f"p{i+1}" , output3)) for i in range(3)]
    for p in procs3:
        p.start()


    while any(p.is_alive() for p in procs3):
        time.sleep(0.8)

    return {
        "scenario1 ":list(output1),
        "scenario2 ":list(output2),
        "scenario3 ":list(output3)
    }


def square(x):
    return x * x

def worker(val, output):
    result = square(val)
    output.append(f"{current_process().name} - square({val}) = {result} ----> {datetime.now()}")
    output.append(result)




def process_pool_scenarios():
    """
    REWORKED: implements your three scenarios with multiprocessing.Process
    (no Pool, so no uvicorn/daemon crash or 'Network Error').
      - scenario 1: for each proc, start() then join() immediately (per-proc)
      - scenario 2: start all, then join all
      - scenario 3: start all, then wait via is_alive() polling (no joins in the main loop)
    """
    manager = multiprocessing.Manager()

    def _worker(idx: int, out_list):
        out_list.append(f"P{idx} starting (pid={os.getpid()})")
        # small workload
        for j in range(idx + 1):
            out_list.append(f"P{idx} step {j}")
            time.sleep(0.05)
        out_list.append(f"P{idx} exiting")

    # Scenario 1
    out1 = manager.list()
    procs1 = [multiprocessing.Process(target=_worker, args=(i, out1), name=f"P{i}") for i in range(4)]
    for p in procs1:
        p.start()
        p.join()

    # Scenario 2
    out2 = manager.list()
    procs2 = [multiprocessing.Process(target=_worker, args=(i, out2), name=f"P{i}") for i in range(4)]
    for p in procs2:
        p.start()
    for p in procs2:
        p.join()

    # Scenario 3
    out3 = manager.list()
    procs3 = [multiprocessing.Process(target=_worker, args=(i, out3), name=f"P{i}") for i in range(4)]
    for p in procs3:
        p.start()
    # busy-wait using is_alive (no joins inside the waiting loop)
    while any(p.is_alive() for p in procs3):
        time.sleep(0.05)
    # optional short join to reap processes (non-blocking if finished)
    for p in procs3:
        p.join(timeout=0.1)

    return {
        "scenario 1": list(out1),
        "scenario 2": list(out2),
        "scenario 3": list(out3)
    }



# -----------------------------------------
# Helper: dispatcher
# -----------------------------------------

def dispatch_scenario(req: ScenarioRequest) -> Dict[str, Any]:
    t = req.type.lower(); task = req.scenario_task
    scenarioNumber = req.scenario_number
    if t == "thread":
        if not (1 <= task <= 7): raise ValueError("Invalid thread scenario_task (must be 1..7)")
        if scenarioNumber not in (1,2,3):
            raise HTTPException(
                    status_code=404,
                    detail="you should enter the valid number from (1,2,3) scenarios...!!!")

        return {
            1: thread_defining_scenarios,
            2: thread_current_scenarios,
            3: thread_subclass_scenarios,
            4: thread_with_lock_scenarios,
            5: thread_with_rlock_scenarios,
            6: thread_with_semaphore_scenarios,
            7: thread_with_barrier_scenarios,
        }[task]()
    elif t == "process":
        if not (1 <= task <= 8): raise ValueError("Invalid process scenario_task (must be 1..8)")
        if scenarioNumber not in (1,2,3):
            raise HTTPException(
                    status_code=404,
                    detail="you should enter the valid number from (1,2,3) scenarios...!!!")

        return {
            1: process_spawn_scenarios,
            2: process_naming_scenarios,
            3: process_background_scenarios,
            4: process_kill_scenarios,
            5: process_subclass_scenarios,
            6: process_queue_scenarios,
            7: process_sync_barrier_scenarios,
            8: process_pool_scenarios,
        }[task]()
    else:
        raise ValueError("Invalid type. Must be 'thread' or 'process'.")

# --------------------------
# Normalizer (stable shape for UI)
# --------------------------
def _dict_strip_keys(d: Dict[str, Any]) -> Dict[str, Any]:
    return { (k.strip() if isinstance(k, str) else k): v for k, v in d.items() }

def normalize_result(raw: Any) -> Dict[str, Any]:
    """
    Output:
    {
      "sections": [ {"title": "...", "items": [...]}, ... ],
      "meta": {...},
      "extras": [ {"title": "...","items":[...]} ]
    }
    """
    sections: List[Dict[str, Any]] = []
    meta: Dict[str, Any] = {}
    extras: List[Dict[str, Any]] = []

    if isinstance(raw, dict):
        raw = _dict_strip_keys(raw)

        # Primary: any keys that start with 'scenario'
        scenario_like = {k: v for k, v in raw.items() if isinstance(k, str) and k.lower().startswith("scenario")}
        if not scenario_like and "results" in raw and isinstance(raw["results"], dict):
            scenario_like = _dict_strip_keys(raw["results"])

        # Meta/extras
        for k, v in raw.items():
            lk = k.lower()
            if lk.startswith("scenario"):  # already handled
                continue
            if lk in ("timer", "status"):
                meta[k] = v
            elif lk in ("sorted_log", "sorted_log:"):
                items = v["sorted_log"] if isinstance(v, dict) and "sorted_log" in v else v
                extras.append({"title": "sorted_log", "items": items if isinstance(items, list) else [items]})
            elif k != "results":
                # Anything else that isn't a scenario is meta
                meta[k] = v

        # Build sections
        for k, v in scenario_like.items():
            items: List[str]
            if isinstance(v, list):
                items = [str(x) for x in v]
            elif isinstance(v, dict):
                # turn dict into label: value lines
                items = [f"{kk}: {vv}" for kk, vv in v.items()]
            else:
                items = [str(v)]
            sections.append({"title": k, "items": items})
    else:
        sections = [{"title": "Output", "items": [str(raw)]}]

    return {"sections": sections, "meta": meta, "extras": extras}



def filter_result_by_scenario(raw: Any, scenario_number: Optional[int]) -> Any:
    """
    Return a copy of raw that keeps ONLY the selected scenario (1..3),
    handling both top-level and nested 'results' dicts,
    and masking variations in keys like 'scenario1 ', 'scenario 1:', etc.
    If scenario_number is None or invalid or nothing matches, returns raw unchanged.
    """
    if not isinstance(raw, dict) or not isinstance(scenario_number, int):
        return raw
    if scenario_number not in (1, 2, 3):
        raise HTTPException(
                status_code=404,
                detail="شما باید تعداد مجاز سناریو را در این بخش (۱،۲،۳) وارد کنید ...!!!")

    def key_matches(k: str, n: int) -> bool:
        # normalize e.g. "Scenario 1", "scenario1 ", "scenario 1:", etc.
        s = ''.join(ch for ch in k.lower() if ch.isalnum())
        return s == f"scenario{n}"

    # Work on a shallow copy
    filtered = dict(raw)

    # Case 1: scenarios are nested under "results"
    if isinstance(filtered.get("results"), dict):
        res = filtered["results"]
        keep = {k: v for k, v in res.items() if key_matches(k, scenario_number)}
        if keep:
            filtered["results"] = keep
            # if there are other scenario keys at top-level, don't touch them (meta stays)
            return filtered

    # Case 2: scenario keys live at top-level
    scenario_keys = [k for k in filtered.keys() if key_matches(k, scenario_number)]
    if scenario_keys:
        # Drop other scenario-* keys at top level
        non_scenario = {k: v for k, v in filtered.items()
                        if not (''.join(ch for ch in k.lower() if ch.isalnum())).startswith("scenario")}
        # Put back the *selected* scenario only
        for k in scenario_keys:
            non_scenario[k] = filtered[k]
        return non_scenario

    # If nothing matched, just return raw
    return raw


#------------------------------------------
# Test
#------------------------------------------


class DevToolkit:
    """
    A small collection of dev / testing helpers that use:
      aiohttp, httpx, networkx, requests-oauthlib, typer (and mention pyinstaller/pytest)
    Designed to be safe (timeouts, try/except) and suitable to run inside Docker.
    """

    def __init__(self, httpx_timeout: float = 5.0, aiohttp_timeout: float = 5.0):
        self.httpx_timeout = httpx_timeout
        self.aiohttp_timeout = aiohttp_timeout

    def fetch_with_httpx(self, url: str) -> Dict[str, Any]:
        """
        Synchronous HTTP GET using httpx with a short timeout.
        Returns dict with `status_code`, `headers` (subset) and `text_snippet`.
        """
        if not url:
            raise ValueError("url is required")
        try:
            with httpx.Client(timeout=self.httpx_timeout) as client:
                r = client.get(url)
                snippet = (r.text[:1000] + "...") if r.text else ""
                return {
                    "ok": True,
                    "transport": "httpx",
                    "status_code": r.status_code,
                    "content_type": r.headers.get("content-type"),
                    "text_snippet": snippet
                }
        except Exception as e:
            logger.exception("httpx fetch failed")
            return {"ok": False, "transport": "httpx", "error": str(e)}

    async def fetch_with_aiohttp(self, url: str) -> Dict[str, Any]:
        """
        Async HTTP GET using aiohttp with timeout.
        Returns similar shape to fetch_with_httpx.
        """
        if not url:
            raise ValueError("url is required")
        try:
            timeout = aiohttp.ClientTimeout(total=self.aiohttp_timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    text = await resp.text()
                    snippet = (text[:1000] + "...") if text else ""
                    return {
                        "ok": True,
                        "transport": "aiohttp",
                        "status_code": resp.status,
                        "content_type": resp.headers.get("content-type"),
                        "text_snippet": snippet
                    }
        except Exception as e:
            logger.exception("aiohttp fetch failed")
            return {"ok": False, "transport": "aiohttp", "error": str(e)}

    def build_graph(self, n: int = 5) -> Dict[str, Any]:
        """
        Build a simple undirected graph with n nodes and return small stats.
        """
        try:
            n = max(0, int(n))
        except Exception:
            n = 5
        G = nx.Graph()
        for i in range(n):
            G.add_node(i)
        # connect sequential nodes and random edge
        for i in range(max(0, n - 1)):
            G.add_edge(i, i + 1)
        if n >= 3:
            G.add_edge(0, n - 1)
        return {
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "is_connected": nx.is_connected(G) if G.number_of_nodes() > 0 else False,
            "sample_adjacency": {str(n): list(G.adj[n]) for n in list(G.nodes())[:min(5, G.number_of_nodes())]}
        }

    def oauth_demo(self) -> Dict[str, Any]:
        """
        Demonstration of constructing an OAuth2Session for authorization_url.
        Uses dummy client_id / redirect_uri — does NOT contact the provider.
        This is purely illustrative and safe.
        """
        try:
            client_id = "YOUR_CLIENT_ID"
            redirect_uri = "https://example.com/callback"
            scope = ["profile"]

            oauth = OAuth2Session(client_id=client_id, redirect_uri=redirect_uri, scope=scope)
            # authorization_url normally requires a real provider; we construct a fake one for illustration
            authorization_url = oauth.authorization_url("https://provider.example.com/auth")[0]
            return {
                "ok": True,
                "method": "requests-oauthlib (OAuth2Session)",
                "authorization_url": authorization_url,
                "note": "This is illustrative. Replace client_id and provider URL for real flows."
            }
        except Exception as e:
            logger.exception("oauth_demo failed")
            return {"ok": False, "error": str(e)}

    def typer_demo(self, name: str = "dev") -> Dict[str, Any]:
        """
        Demonstrate a callable that can be wired to a Typer CLI.
        We'll execute the function directly (not run a CLI).
        """
        app = typer.Typer()

        @app.command()
        def greet(who: str = name):
            print(f"Hello, {who} (Typer demo)")

        # call the function directly (simulates invoking a CLI callback)
        try:
            # call our inner function to simulate its behavior
            greet_callback_output = f"Hello, {name} (Typer demo - called programmatically)"
            return {"ok": True, "message": greet_callback_output}
        except Exception as e:
            logger.exception("typer_demo failed")
            return {"ok": False, "error": str(e)}

    def pyinstaller_hint(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "pyinstaller": "To bundle: `pyinstaller --onefile your_script.py`. Note: Test in container/CI; resources may need --add-data."
        }

    def pytest_hint(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "pytest": "Run tests: `pytest -q`. In Docker, run `docker run --rm <image> pytest -q` or run them in CI."
        }


# single toolkit instance (fast to create)
toolkit = DevToolkit()


# -----------------------------------------
# Routes
# -----------------------------------------

@app.get("/dev/toolbox")
async def dev_toolbox(
    action: str = Query(..., description="Action: httpx | aiohttp | graph | oauth | pyinstaller | pytest | typer"),
    url: Optional[str] = Query(None, description="URL for http fetch actions"),
    n: Optional[int] = Query(5, description="n (for graph)"),
):
    """
    Unified dev endpoint. Example:
      GET /dev/toolbox?action=httpx&url=https://example.com
      GET /dev/toolbox?action=aiohttp&url=https://example.com
      GET /dev/toolbox?action=graph&n=6
      GET /dev/toolbox?action=oauth
      GET /dev/toolbox?action=pyinstaller
      GET /dev/toolbox?action=pytest
      GET /dev/toolbox?action=typer&name=bob
    """
    action_lower = action.lower()
    try:
        if action_lower == "httpx":
            if not url:
                raise HTTPException(status_code=400, detail="url is required for httpx action")
            result = toolkit.fetch_with_httpx(url)
            return JSONResponse({"action": "httpx", "input_url": url, "result": result})

        elif action_lower == "aiohttp":
            if not url:
                raise HTTPException(status_code=400, detail="url is required for aiohttp action")
            result = await toolkit.fetch_with_aiohttp(url)
            return JSONResponse({"action": "aiohttp", "input_url": url, "result": result})

        elif action_lower == "graph":
            result = toolkit.build_graph(n or 5)
            return JSONResponse({"action": "graph", "n": n, "result": result})

        elif action_lower == "oauth":
            result = toolkit.oauth_demo()
            return JSONResponse({"action": "oauth_demo", "result": result})

        elif action_lower == "pyinstaller":
            return JSONResponse({"action": "pyinstaller_info", "result": toolkit.pyinstaller_hint()})

        elif action_lower == "pytest":
            return JSONResponse({"action": "pytest_info", "result": toolkit.pytest_hint()})

        elif action_lower == "typer":
            name = Query(None)
            # call the demo with provided name via query param if desired
            # Note: we don't parse additional query params here to keep API simple
            result = toolkit.typer_demo(name="dev")
            return JSONResponse({"action": "typer_demo", "result": result})

        else:
            raise HTTPException(status_code=400, detail=f"unknown action: {action}")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("dev_toolbox error")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dev/debug")
def dev_debug():
    """
    Return versions and small environment details to help debug inside Docker.
    """
    try:
        info = {
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
            "cwd": os.getcwd(),
            "packages": {
                "httpx": getattr(httpx, "__version__", "unknown"),
                "aiohttp": getattr(aiohttp, "__version__", "unknown"),
                "networkx": getattr(nx, "__version__", "unknown"),
                "requests-oauthlib": "installed (requests-oauthlib)",
                "typer": getattr(typer, "__version__", "unknown"),
            }
        }
        return JSONResponse({"ok": True, "environment": info})
    except Exception as e:
        logger.exception("dev_debug error")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)



@app.get("/health")
def health_check():
    return {"status": "ok", "message": f"Server is running, time={time.time()}"}


@app.get("/", response_class=HTMLResponse)
def serve_index():
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return HTMLResponse("<h3>Place your index.html into ./static/ and restart the server</h3>", status_code=200)



@app.post("/run_scenarios")
def run_scenarios(req: ScenarioRequest):
    """
    Synchronous endpoint; browser waits until computation finishes.
    Returns both raw result and normalized sections for clean UI rendering.
    """
    try:
        # Run whatever function matches (your dispatch logic stays the same)
        raw_result = dispatch_scenario(req)

        # NEW: keep only the selected scenario if provided (1..3)
        raw_result = filter_result_by_scenario(raw_result, req.scenario_number)

        # Explanation text (as you already had)
        explanation_text = SERVER_TASK_DESCRIPTIONS.get(req.type.lower(), {}).get(
            req.scenario_task, "توضیحی موجود نیست."
        )

        # Normalize AFTER filtering so UI only sees the chosen scenario
        normalized = normalize_result(raw_result)

        return JSONResponse(
            status_code=200,
            content={
                "message": "Scenario executed",
                "data": {
                    "type": req.type,
                    "scenario_task": req.scenario_task,
                    "scenario_number": req.scenario_number
                },
                "result": raw_result,      # filtered original (kept for debugging)
                "normalized": normalized,  # stable for UI (only one scenario section now)
                "explanation": explanation_text
            }
        )
    except Exception as e:
        logging.exception("Error while running scenario")
        raise HTTPException(status_code=400, detail=str(e))


cli = typer.Typer()

@cli.command()
def hello(name: str = "world"):
    print(f"Hello {name} from Typer!")



# -----------------------------------------
# If run directly, use uvicorn (optional)
# -----------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

