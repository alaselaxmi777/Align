"""ALIGN Maharashtra SYNTHETIC dataset generator (v3.0). Deterministic (seed 11).
Synthetic, dev/eval only. Random name combinations may coincide with real people: never treat as real.
Usage: python generate_maharashtra_dataset.py <output_dir>"""
import json, random, os, sys, re, statistics
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clusters_base import K
random.seed(11)
OUT = sys.argv[1] if len(sys.argv) > 1 else "."
N_USERS, N_COMM, N_EVENTS, N_ACT = 1500, 400, 800, 500

# ---------- Maharashtra cities (approximate city-centre coordinates, city-level precision) ----------
CITIES = {"Pune":(18.520,73.857,.20),"Mumbai":(19.076,72.878,.14),"Kolhapur":(16.705,74.243,.15),"Nagpur":(21.146,79.088,.08),
 "Nashik":(19.998,73.790,.07),"Thane":(19.218,72.978,.05),"Sangli":(16.854,74.582,.06),"Satara":(17.680,74.018,.04),
 "Solapur":(17.660,75.906,.05),"Chhatrapati Sambhajinagar":(19.876,75.343,.05),"Ichalkaranji":(16.691,74.460,.03),
 "Ratnagiri":(16.990,73.300,.03),"Amravati":(20.933,77.751,.05)}
CN=list(CITIES); CW=[CITIES[c][2] for c in CN]
def pick_city(): return random.choices(CN,CW)[0]
def loc(city=None):
    city=city or pick_city(); la,lo,_=CITIES[city]
    return {"state":"Maharashtra","city":city,"approx_lat":round(la+random.uniform(-.03,.03),2),"approx_lng":round(lo+random.uniform(-.03,.03),2),"precision":"approximate"}

# ---------- local clusters (kind, interests, skills, topics, activities, hand queries, goal phrase, related) ----------
NEW = {
"kabaddi":("lifestyle",["Kabaddi and Kho-Kho","Fitness"],[],["kabaddi","kho-kho","traditional Indian sports"],["practise raids and defence drills","organise friendly local matches","train fitness for kabaddi"],
  ["Join a kabaddi team","I want to play traditional Indian sports regularly","Find players for local kho-kho matches"],"kabaddi",["kushti","sports","running"]),
"kushti":("lifestyle",["Kushti and Wrestling","Fitness"],[],["kushti","wrestling","akhada training"],["train traditional wrestling moves","build strength with a group","learn akhada routines"],
  ["Find a kushti training group","I want to learn traditional wrestling","Strength training in an akhada-style group"],"kushti and wrestling",["kabaddi","sports","running"]),
"sahitya":("creative",["Marathi Literature","Writing"],["Writing"],["Marathi literature","Marathi poetry","storytelling"],["read and discuss Marathi poems and stories","share original writing","host kavi sammelan style readings"],
  ["Meet people who read and write Marathi poetry","I want feedback on my Marathi short stories","A group to discuss Marathi books"],"Marathi literature",["reading","natak","speaking"]),
"natak":("creative",["Theatre and Drama"],["Acting"],["Marathi theatre","drama and acting","street plays"],["rehearse short plays","practise acting and voice","write and stage street plays"],
  ["Join a Marathi theatre group","I want to try acting on stage","Find people to stage a street play"],"theatre and drama",["sahitya","speaking","folk_dance"]),
"classical_music":("creative",["Indian Classical Music"],["Classical Vocal","Tabla"],["Indian classical music","bhajan and devotional music","natyasangeet"],["practise ragas and bhajans","learn tabla and harmonium","hold small music baithaks"],
  ["Learn Indian classical vocal with others","I want to join a bhajan group","Find tabla and harmonium learners"],"Indian classical music",["music","folk_dance"]),
"folk_dance":("creative",["Folk Dance"],["Dance"],["lavani and folk dance","Maharashtrian folk art","garba and dandiya"],["learn folk dance steps","rehearse for cultural programs","practise garba and lavani"],
  ["Learn lavani and folk dance","I want to join a garba practice group","Cultural dance classes for beginners"],"folk dance",["classical_music","natak","ganesh"]),
"forts":("lifestyle",["Fort Trekking","Trekking and Hiking"],[],["fort trekking","Sahyadri treks","historical forts of Maharashtra"],["plan fort treks in the Sahyadri","learn the history of forts","share safe trekking tips"],
  ["Go on Maharashtra fort treks on weekends","I love history and want to visit old forts with a group","Monsoon treks in the Sahyadri"],"fort trekking",["trek","photo"]),
"ganesh":("social",["Ganeshotsav and Festivals","Volunteering"],["Event Organizing"],["Ganeshotsav","festival celebrations","cultural programs"],["organise eco-friendly Ganeshotsav activities","plan cultural evenings","coordinate festival volunteers"],
  ["Join Ganeshotsav eco-friendly activities","I want to help organise festival programs in my area","Volunteer for cultural events"],"festival organising",["folk_dance","volunteer","handicraft"]),
"mpsc":("career",["Competitive Exam Prep (MPSC/UPSC)","Career Development"],["Writing"],["MPSC and UPSC preparation","competitive exam study","current affairs"],["run mock tests and answer writing","discuss current affairs","share study plans"],
  ["Study group for MPSC preparation","I am preparing for government exams and need peers","Current affairs discussion for UPSC aspirants"],"MPSC and UPSC preparation",["placements","reading","research"]),
"agri":("business",["Agriculture and AgriTech"],["Data Analysis"],["agriculture and AgriTech","modern farming","farm data and sensors"],["discuss modern farming practices","explore AgriTech tools","share crop and market knowledge"],
  ["Meet people using technology in farming","I want to learn modern agriculture methods","AgriTech ideas for small farmers"],"AgriTech",["data","robotics","volunteer"]),
"maha_food":("lifestyle",["Maharashtrian Cooking","Cooking"],["Cooking"],["Maharashtrian cooking","festival sweets and snacks","regional recipes"],["cook puran poli and misal together","swap family recipes","prepare festival faral"],
  ["Learn to cook Maharashtrian dishes","I want to make puran poli and modak at home","Recipe swap for traditional festival food"],"Maharashtrian cooking",["cooking","ganesh"]),
"handicraft":("creative",["Handicrafts and Rangoli","Drawing and Painting"],[],["rangoli and handicrafts","traditional crafts","festival decoration"],["practise rangoli designs","make festival decorations","share craft techniques"],
  ["Learn rangoli and handicrafts","I want to make festival decorations with a group","Craft circle for beginners"],"handicrafts and rangoli",["ganesh","design"]),
}
K.update(NEW)
# make relations symmetric-ish for old clusters
ADD={"trek":["forts"],"cooking":["maha_food"],"music":["classical_music"],"reading":["sahitya"],"sports":["kabaddi"],"running":["kabaddi","kushti"],"volunteer":["ganesh"],"design":["handicraft"],"placements":["mpsc"],"data":["agri"]}
for k,v in ADD.items(): K[k]=K[k][:7]+(list(dict.fromkeys(list(K[k][7])+v)),)
KEYS=list(K)

TOPIC_MR={"ai_ml":"कृत्रिम बुद्धिमत्ता व मशीन लर्निंग","python":"पायथॉन प्रोग्रामिंग","web":"वेब डेव्हलपमेंट","data":"डेटा सायन्स","placements":"प्लेसमेंट तयारी","cyber":"सायबर सुरक्षा",
 "photo":"फोटोग्राफी","design":"यूआय/यूएक्स डिझाइन","entre":"उद्योजकता","speaking":"सार्वजनिक भाषण","opensource":"ओपन सोर्स","cp":"कॉम्पिटिटिव्ह प्रोग्रामिंग","robotics":"रोबोटिक्स व आयओटी",
 "running":"धावणे व फिटनेस","trek":"ट्रेकिंग","chess":"बुद्धिबळ","sports":"क्रिकेट व मैदानी खेळ","reading":"वाचन व लेखन","volunteer":"स्वयंसेवा व पर्यावरण","content":"कंटेंट क्रिएशन",
 "freelance":"फ्रीलान्सिंग","language":"भाषा सराव","research":"संशोधन","cloud":"क्लाउड व डेव्हऑप्स","music":"संगीत","cooking":"स्वयंपाक","finance":"वैयक्तिक वित्त व गुंतवणूक","yoga":"योग व ध्यान",
 "mobile":"मोबाइल ॲप डेव्हलपमेंट","gamedev":"गेम डेव्हलपमेंट","kabaddi":"कबड्डी व खो-खो","kushti":"कुस्ती व व्यायामशाळा","sahitya":"मराठी साहित्य व कविता","natak":"नाटक व रंगभूमी",
 "classical_music":"शास्त्रीय संगीत व भजन","folk_dance":"लावणी व लोकनृत्य","forts":"गडकिल्ले भ्रमंती","ganesh":"गणेशोत्सव व सांस्कृतिक उपक्रम","mpsc":"स्पर्धा परीक्षा तयारी","agri":"शेती व कृषी तंत्रज्ञान",
 "maha_food":"महाराष्ट्रीय पाककला","handicraft":"रांगोळी व हस्तकला"}
Q_MR={"ai_ml":"मला कृत्रिम बुद्धिमत्ता शिकायची आहे आणि एआय प्रोजेक्ट बनवणाऱ्या लोकांना भेटायचे आहे","python":"मला उत्तम प्रोग्रामर व्हायचे आहे, सराव करायला मित्र हवेत","web":"वेबसाइट कशी बनवायची आणि प्रकाशित कशी करायची हे शिकायचे आहे",
 "data":"डेटा सायन्सचा अभ्यास करण्यासाठी अभ्यासगट शोधा","placements":"कॅम्पस प्लेसमेंटसाठी तयारी करायला मदत हवी आहे","cyber":"एथिकल हॅकिंग आणि सायबर सुरक्षा शिकायची आहे","photo":"माझे फोटो अधिक चांगले काढायला शिकायचे आहे, फोटोवॉक गट कुठे आहे",
 "design":"अॅप आणि वेबसाइटचे डिझाइन शिकण्यासाठी लोक शोधा","entre":"मला स्वतःचा व्यवसाय सुरू करायचा आहे, उद्योजकांना भेटायचे आहे","speaking":"स्टेजवर बोलताना भीती वाटते, आत्मविश्वासाने बोलायला शिकायचे आहे",
 "opensource":"ओपन सोर्स प्रकल्पांमध्ये योगदान कसे द्यायचे ते शिकायचे आहे","cp":"स्पर्धात्मक कोडिंगसाठी सहकारी शोधत आहे","robotics":"सेन्सर वापरून इलेक्ट्रॉनिक्स प्रकल्प बनवायचे आहेत","running":"सकाळी सोबत धावण्यासाठी गट हवा आहे",
 "trek":"आठवड्याच्या शेवटी ट्रेकला जायला कोण येणार","chess":"बुद्धिबळ खेळायला सोबती हवेत","sports":"रविवारी क्रिकेट खेळायला संघ शोधतोय","reading":"पुस्तक चर्चा मंडळात सहभागी व्हायचे आहे",
 "volunteer":"पर्यावरणासाठी स्वयंसेवक म्हणून काम करायचे आहे","content":"छोटे व्हिडिओ बनवून प्रेक्षक वाढवायचे आहेत","freelance":"फ्रीलान्सिंग सुरू करून ग्राहक मिळवायचे आहेत","language":"इंग्रजी बोलण्याचा सराव करायला जोडीदार हवा आहे",
 "research":"संशोधन पेपर वाचणाऱ्या लोकांना भेटायचे आहे","cloud":"क्लाउड आणि कंटेनर शिकायचे आहेत","music":"गिटार वाजवणाऱ्या लोकांसोबत जॅम सेशन करायचे आहे","cooking":"घरी चांगले जेवण बनवायला शिकायचे आहे",
 "finance":"गुंतवणुकीची मूलभूत माहिती शिकायची आहे","yoga":"रोज सकाळी योग आणि ध्यान करणारा गट हवा आहे","mobile":"मोबाइल ॲप बनवायचे आहे आणि प्ले स्टोअरवर टाकायचे आहे","gamedev":"स्वतःचा गेम बनवायला शिकायचे आहे",
 "kabaddi":"कबड्डी खेळायला आणि सराव करायला संघ हवा आहे","kushti":"कुस्तीचा सराव करायला तालीम किंवा गट शोधतोय","sahitya":"मराठी कविता आणि कथा वाचणाऱ्या आणि लिहिणाऱ्यांना भेटायचे आहे","natak":"नाटकात काम करायला आणि रंगभूमीवर शिकायला संधी हवी आहे",
 "classical_music":"शास्त्रीय संगीत आणि भजन शिकणाऱ्या लोकांचा गट हवा आहे","folk_dance":"लावणी आणि लोकनृत्य शिकण्यासाठी वर्ग किंवा गट हवा आहे","forts":"शिवकालीन गडकिल्ल्यांवर भ्रमंतीसाठी सोबती हवेत","ganesh":"गणेशोत्सवात पर्यावरणपूरक उपक्रमांमध्ये सहभागी व्हायचे आहे",
 "mpsc":"एमपीएससी परीक्षेचा अभ्यास करण्यासाठी अभ्यासगट हवा आहे","agri":"शेतीमध्ये आधुनिक तंत्रज्ञान वापरणाऱ्या लोकांना भेटायचे आहे","maha_food":"पुरणपोळी आणि मिसळ यांसारख्या पारंपरिक पाककृती शिकायच्या आहेत","handicraft":"रांगोळी आणि हस्तकला शिकायची आहे"}
Q_HI={"ai_ml":"Mujhe AI seekhna hai aur AI projects banane wale log chahiye","python":"Coding mein better hona hai, practice karne ke liye dost chahiye","web":"Website banana aur deploy karna seekhna hai","data":"Data science ke liye study group chahiye",
 "placements":"Campus placement ki taiyari mein help chahiye","cyber":"Ethical hacking aur cyber security seekhni hai","photo":"Mere photos aur achhe lene hain, photowalk group kahan hai","design":"App aur website design seekhne ke liye log chahiye",
 "entre":"Apna business shuru karna hai, aise log milne chahiye","speaking":"Stage par bolne mein darr lagta hai, confidence badhana hai","opensource":"Open source mein contribute kaise karein, seekhna hai","cp":"Competitive coding ke liye teammates chahiye",
 "robotics":"Sensors se electronics projects banane hain","running":"Subah saath mein running karne wala group chahiye","trek":"Weekend par trekking pe jaana hai, koi aa raha hai kya","chess":"Chess khelne ke liye partner chahiye",
 "sports":"Sunday ko cricket khelne ke liye team dhoondh raha hoon","reading":"Book club join karna hai","volunteer":"Environment ke liye volunteer banna hai","content":"Short videos bana kar audience badhani hai",
 "freelance":"Freelancing start karke clients dhoondhne hain","language":"English bolne ki practice ke liye partner chahiye","research":"Research papers padhne wale logon se milna hai","cloud":"Cloud aur containers seekhne hain",
 "music":"Guitar bajane wale logon ke saath jam session karna hai","cooking":"Ghar par achha khana banana seekhna hai","finance":"Investing ki basics seekhni hain","yoga":"Roz subah yoga aur meditation ka group chahiye",
 "mobile":"Mobile app banana hai aur Play Store par daalna hai","gamedev":"Apna game banana seekhna hai","kabaddi":"Kabaddi khelne aur practice karne ke liye team chahiye","kushti":"Kushti ki practice ke liye talim ya group dhoondh raha hoon",
 "sahitya":"Marathi kavita aur kahani padhne likhne wale log chahiye","natak":"Natak mein kaam karna hai, theatre seekhna hai","classical_music":"Shastriya sangeet aur bhajan seekhne wala group chahiye","folk_dance":"Lavani aur folk dance seekhne ke liye class chahiye",
 "forts":"Shivkaleen gadkille dekhne ke liye trek partners chahiye","ganesh":"Ganeshotsav mein eco-friendly activities mein hissa lena hai","mpsc":"MPSC exam ki padhai ke liye study group chahiye","agri":"Kheti mein modern technology use karne wale logon se milna hai",
 "maha_food":"Puran poli aur misal jaisi traditional recipes seekhni hain","handicraft":"Rangoli aur handicrafts seekhne hain"}
assert set(TOPIC_MR)==set(KEYS)==set(Q_MR)==set(Q_HI), set(KEYS)^set(Q_MR)

EXTRA_TITLES={"kabaddi":["Local Kabaddi Tournament","Kho-Kho Practice Match Day"],"kushti":["Kushti Practice Day","Akhada Fitness Meetup"],"sahitya":["Kavi Sammelan Evening","Marathi Book Discussion Evening","Katha Vachan Session"],
 "natak":["Natak Reading Session","Street Play Rehearsal Day","Acting Workshop for Beginners"],"classical_music":["Bhajan Sandhya","Raag Practice Baithak","Tabla Beginners Session"],"folk_dance":["Garba and Dandiya Night","Lavani Dance Workshop","Folk Dance Rehearsal Day"],
 "forts":["Sahyadri Monsoon Trek","Fort History Walk","Shivjayanti Fort Trek"],"ganesh":["Eco-friendly Ganesh Idol Workshop","Ganeshotsav Cultural Evening","Gudi Padwa Community Gathering","Festival Clean-up Drive"],
 "mpsc":["MPSC Mock Test Day","Current Affairs Discussion","UPSC Answer Writing Practice"],"agri":["AgriTech Meetup for Farmers","Modern Farming Talk","Soil and Crop Data Workshop"],
 "maha_food":["Diwali Faral Cooking Session","Puran Poli Cooking Day","Modak Making Workshop"],"handicraft":["Diwali Rangoli Competition","Festival Decoration Workshop","Rangoli Design Practice Day"]}
def ecat_of(title):
    t=title.lower()
    if re.search("tournament|competition|match|challenge",t): return "Competition"
    if re.search("workshop|session|practice|rehearsal|mock",t): return "Workshop"
    if re.search("talk|discussion",t): return "Talk"
    if re.search("night|sandhya|baithak|gathering|evening|meetup|walk|trek|day",t): return "Meetup"
    return "Social"

AUD=["students","beginners","working professionals","hobbyists","final-year students","self-learners","first-year students","career switchers","homemakers","retired enthusiasts"]
SUFFIX=["Circle","Katta","Mandal","Manch","Parivar","Sangh","Club","Collective","Group","Hub"]
KIND_ECATS={"tech":["Workshop","Meetup","Talk","Hackathon","Competition","Webinar"],"creative":["Workshop","Meetup","Talk","Competition","Social"],"career":["Workshop","Networking","Talk","Webinar","Meetup"],
 "business":["Talk","Networking","Webinar","Workshop","Competition"],"lifestyle":["Meetup","Social","Competition","Workshop"],"social":["Social","Meetup","Workshop"]}
KIND_CCAT={"tech":"Technology","creative":"Creative","career":"Career","business":"Entrepreneurship","lifestyle":"Hobby","social":"Social Impact"}
KIND_ACAT={"tech":["Study Group","Skill Session","Hackathon","Learning Session"],"creative":["Creative Session","Skill Session","Workshop"],"career":["Learning Session","Networking","Study Group"],
 "business":["Workshop","Networking","Learning Session"],"lifestyle":["Sports","Creative Session","Networking","Study Group"],"social":["Volunteering","Networking"]}
SPORTY={"running","trek","sports","yoga","kabaddi","kushti","forts"}
ETITLE={"Workshop":["{T} Workshop","Hands-on {T} Session","Intro to {T}","Beginner's Guide to {T}"],"Meetup":["{T} Meetup","{T} Community Evening"],"Talk":["Getting Started with {T}","{T}: Lessons Learned"],
 "Networking":["{T} Networking Evening"],"Competition":["{T} Challenge Day"],"Webinar":["{T} Webinar"],"Hackathon":["{T} Mini Hackathon"],"Social":["{T} Social Day"]}
CDESC=["A {size} group where {aud} {act} and {act2}.","Open to {aud} who want to {act}. Regular sessions focus on {topic}.","We help {aud} {act}.","Peer-led community for {topic}: members {act} and share honest feedback.",
 "Meet people who care about {topic}. Members {act}, and discussion stays friendly.","A space for {aud} to {act} and learn {topic} together."]
ADESC=["Join others to {act}. Suitable for {aud}.","A small session to {act}. Beginners are welcome.","Regular practice where people {act}.","Come along to {act} and meet like-minded people."]
EDESC=["A {lvl} {fmt} on {topic}. You will {act}.","{lvl} session about {topic}. Expect to {act}.","Learn about {topic} with peers. Together we will {act}."]
MR_C=["{t} विषयात रस असणाऱ्यांसाठी मैत्रीपूर्ण गट. नियमित भेटी, चर्चा आणि अनुभवांची देवाणघेवाण.","{t} शिकू इच्छिणाऱ्या आणि सराव करू इच्छिणाऱ्यांसाठी खुला समुदाय. नवशिक्यांचे स्वागत आहे.","{t} आवडणाऱ्या लोकांसाठी एकत्र येण्याचे ठिकाण. दर आठवड्याला भेटी आणि सराव."]
MR_E=["{t} वरील नवशिक्यांसाठी सत्र. सहभागी होऊन प्रत्यक्ष सराव करा.","{t} विषयी शिका आणि इतरांशी ओळख करून घ्या."]
MR_A=["{t} साठी एकत्र सराव करण्याचे सत्र. नवशिक्यांचे स्वागत आहे.","{t} आवडणाऱ्या लोकांसोबत नियमित सराव."]
HI_C=["{t} mein interest rakhne walon ke liye ek friendly group. Regular meetups aur discussions.","{t} seekhne aur practice karne ke liye open community. Beginners ka swagat hai."]
HI_E=["{t} par beginners ke liye session. Hissa lekar practice karein.","{t} ke baare mein seekhein aur naye logon se milein."]
HI_A=["{t} ki practice ke liye saath milkar session. Beginners welcome.","{t} pasand karne walon ke saath regular practice."]
def cap(s): return " ".join(w[:1].upper()+w[1:] for w in s.split())
def lang(): return random.choices(["en","mr","hi-latn"],[.7,.2,.1])[0]
def desc(kind_en,kind_mr,kind_hi,k,topic,en_kwargs):
    l=lang()
    if l=="mr": return random.choice(kind_mr).format(t=TOPIC_MR[k]),l
    if l=="hi-latn": return random.choice(kind_hi).format(t=topic),l
    return random.choice(kind_en).format(**en_kwargs),l

# ---------- names (random combinations; synthetic) ----------
FIRST_F=["Rutuja","Snehal","Gauri","Shreya","Pooja","Komal","Ankita","Mayuri","Sakshi","Priya","Neha","Kavita","Sana","Aishwarya","Pallavi","Tanvi","Madhuri","Swati","Rutika","Sayali"]
FIRST_M=["Omkar","Sanket","Pratik","Aditya","Tejas","Nikhil","Vaibhav","Rohit","Swapnil","Prasad","Akash","Amit","Rahul","Imran","Faisal","Ganesh","Yash","Sagar","Onkar","Shubham"]
LAST=["Patil","Jadhav","Deshmukh","Kulkarni","Shinde","Pawar","More","Bhosale","Chavan","Gaikwad","Kadam","Joshi","Deshpande","Mane","Salunkhe","Sawant","Kamble","Shaikh","Khan","Sharma","Gupta","Naik","Desai","Thorat","Yadav","Gawade","Mulik","Phadke","Bhide","Pathan"]
EDU={"tech":[("Engineering student",.45),("Working professional (IT)",.3),("Diploma student",.1),("B.Sc. student",.15)],
 "career":[("Engineering student",.25),("Government exam aspirant",.3),("B.Com. student",.2),("B.Sc. student",.15),("Working professional (non-IT)",.1)],
 "business":[("Small business owner",.3),("Farmer / agri entrepreneur",.15),("B.Com. student",.2),("Engineering student",.2),("Working professional (non-IT)",.15)],
 "creative":[("B.Sc. student",.2),("Engineering student",.2),("Teacher",.15),("Working professional (non-IT)",.25),("Homemaker",.2)],
 "lifestyle":[("Engineering student",.2),("Working professional (non-IT)",.25),("Teacher",.1),("B.Com. student",.15),("Homemaker",.15),("Small business owner",.15)],
 "social":[("Engineering student",.2),("B.Sc. student",.2),("Teacher",.15),("Working professional (non-IT)",.25),("Homemaker",.2)]}
GOALS={"tech":(["Build a project","Learn a new skill","Win a hackathon","Get an internship"],["Get a job in tech","Pursue higher studies","Become a researcher"]),
 "career":(["Prepare for placements","Improve communication","Get an internship","Learn a new skill"],["Get a job in tech","Switch careers","Become a mentor"]),
 "business":(["Build a portfolio","Find study partners","Learn a new skill"],["Start a company","Become a freelancer","Build a personal brand"]),
 "creative":(["Build a portfolio","Learn a new skill"],["Build a personal brand","Become a freelancer","Switch careers"]),
 "lifestyle":(["Learn a new skill","Find study partners"],["Become a mentor","Start a company"]),"social":(["Improve communication","Find study partners"],["Become a mentor","Pursue higher studies"])}
M={"is_synthetic":True,"dataset_version":"3.0","region":"Maharashtra"}
gt={"communities":{},"events":{},"activities":{},"users":{}}

# ---------- communities ----------
communities=[]; used=set()
per=[N_COMM//len(KEYS)+(1 if i<N_COMM%len(KEYS) else 0) for i in range(len(KEYS))]
for k,n in zip(KEYS,per):
    kind,ints,sks,topics,acts,_,_,rel=K[k]
    for _ in range(n):
        for _t in range(60):
            city=pick_city(); t=random.choice(topics); name=f"{city} {cap(t)} {random.choice(SUFFIX)}"
            if name not in used: used.add(name); break
        else: name=f"{name} {len(used)}"; used.add(name)
        a=random.sample(acts,2); sec=random.choice(rel) if random.random()<.35 else None
        d,l=desc(CDESC,MR_C,HI_C,k,t,dict(size=random.choice(["friendly","small","growing","welcoming"]),aud=random.choice(AUD),act=a[0],act2=a[1],topic=t))
        iset=list(ints)+(random.sample(K[sec][1],1) if sec else [])
        cid=f"c{len(communities)+1:04d}"
        communities.append({"id":cid,"name":name,"category":KIND_CCAT[kind],"description":d,"language":l,"interests":iset,
          "skills_supported":random.sample(sks,min(len(sks),random.randint(0,3))) if sks else [],"privacy":random.choices(["public","private"],[.88,.12])[0],
          "member_count_synthetic":random.randint(3,220),"location":loc(city),**M})
        gt["communities"][cid]={"primary":k,"secondary":sec}
random.shuffle(communities)
by_comm=defaultdict(list)
for c in communities: by_comm[gt["communities"][c["id"]]["primary"]].append(c)

# ---------- events ----------
events=[]; per=[N_EVENTS//len(KEYS)+(1 if i<N_EVENTS%len(KEYS) else 0) for i in range(len(KEYS))]
for k,n in zip(KEYS,per):
    kind,ints,sks,topics,acts,_,_,rel=K[k]
    for _ in range(n):
        t=random.choice(topics)
        if k in EXTRA_TITLES and random.random()<.5: title=random.choice(EXTRA_TITLES[k]); ecat=ecat_of(title)
        else: ecat=random.choice(KIND_ECATS[kind]); title=random.choice(ETITLE[ecat]).format(T=cap(t))
        mode=random.choices(["offline","online"],[.75,.25])[0]
        com=random.choice(by_comm[k]) if random.random()<.8 and by_comm[k] else None
        sec=random.choice(rel) if random.random()<.25 else None
        iset=list(ints)+(random.sample(K[sec][1],1) if sec else [])
        d,l=desc(EDESC,MR_E,HI_E,k,t,dict(lvl=random.choice(["Beginner-friendly","Intermediate","All-levels"]),fmt=random.choice(["session","meetup","workshop"]),topic=t,act=random.choice(acts)))
        eid=f"e{len(events)+1:04d}"; city=com["location"]["city"] if com else pick_city()
        events.append({"id":eid,"title":title,"category":ecat,"description":d,"language":l,"interests":iset,"skills":random.sample(sks,min(len(sks),random.randint(0,2))) if sks else [],
          "community_id":com["id"] if com else None,"mode":mode,"days_from_now":random.randint(-30,75),"is_free":random.random()<.78,"capacity":random.choice([15,20,30,50,100,None]),
          "source":"user_created","location":loc(city) if mode=="offline" else None,**M})
        gt["events"][eid]={"primary":k,"secondary":sec}
random.shuffle(events)

# ---------- activities ----------
activities=[]; per=[N_ACT//len(KEYS)+(1 if i<N_ACT%len(KEYS) else 0) for i in range(len(KEYS))]
for k,n in zip(KEYS,per):
    kind,ints,sks,topics,acts,_,_,rel=K[k]
    for _ in range(n):
        acat="Photography Walk" if k=="photo" else ("Sports" if k in SPORTY else random.choice(KIND_ACAT[kind]))
        t=random.choice(topics); a=random.choice(acts); sec=random.choice(rel) if random.random()<.25 else None
        iset=list(ints)+(random.sample(K[sec][1],1) if sec else [])
        d,l=desc(ADESC,MR_A,HI_A,k,t,dict(act=a,aud=random.choice(AUD)))
        aid=f"a{len(activities)+1:04d}"
        activities.append({"id":aid,"title":f"{cap(t)} {random.choice(['Practice','Session','Meetup','Sprint','Hour','Circle','Katta'])}","category":acat,"description":d,"language":l,"interests":iset,
          "skills_developed":random.sample(sks,min(len(sks),random.randint(0,2))) if sks else [],"location":loc(),**M})
        gt["activities"][aid]={"primary":k,"secondary":sec}
random.shuffle(activities)

# ---------- users ----------
BIO_EN=["Interested in {a} and {b}. Looking to meet people who build things.","Exploring {a}; want to get better at {b}.","Into {a}. Currently learning {b}.","Enjoy {a} and {b}. New here and keen to join groups."]
BIO_MR=["{a} मध्ये रस आहे आणि {b} शिकायचे आहे.","{a} आवडते. सध्या {b} शिकत आहे. नवीन लोकांना भेटायला आवडेल."]
BIO_HI=["{a} mein interest hai aur {b} seekhna hai.","{a} pasand hai. Abhi {b} seekh raha hoon."]
users=[]
for i in range(1,N_USERS+1):
    prim=random.choice(KEYS); extra=random.sample([x for x in KEYS if x!=prim],random.choice([0,1,1,2])); cl=[prim]+extra; kind=K[prim][0]
    ints=[]
    for c in cl: ints+=random.sample(K[c][1],min(len(K[c][1]),random.randint(1,len(K[c][1]))))
    ints=list(dict.fromkeys(ints))
    skp=list(dict.fromkeys([s for c in cl for s in K[c][2]]))
    sk=random.sample(skp,min(len(skp),random.randint(0,3))) if skp else []
    learn=[s for s in random.sample(skp,min(len(skp),random.randint(1,3))) if s not in sk] if skp else []
    gs,gl=GOALS[kind]; fem=random.random()<.48
    name=f"{random.choice(FIRST_F if fem else FIRST_M)} {random.choice(LAST)}"
    langs=[l for l,p in (("Marathi",.8),("Hindi",.75),("English",.92)) if random.random()<p]
    if len(langs)<2: langs=list(dict.fromkeys(langs+["Marathi","English"]))
    bl=random.choices(["en","mr","hi-latn"],[.6,.25,.15])[0]
    if bl=="mr": bio=random.choice(BIO_MR).format(a=TOPIC_MR[prim],b=TOPIC_MR[cl[-1]])
    elif bl=="hi-latn": bio=random.choice(BIO_HI).format(a=K[prim][3][0],b=K[cl[-1]][3][0])
    else: bio=random.choice(BIO_EN).format(a=K[prim][3][0],b=K[cl[-1]][3][0])
    edu=random.choices([e for e,_ in EDU[kind]],[w for _,w in EDU[kind]])[0]
    if prim=="agri" and random.random()<.5: edu="Farmer / agri entrepreneur"
    if prim=="mpsc" and random.random()<.6: edu="Government exam aspirant"
    users.append({"id":f"u{i:04d}","display_name":name,"age_range":random.choices(["18-24","25-34","35-44","45-54"],[.6,.28,.08,.04])[0],"occupation_or_study":edu,"bio":bio,"bio_language":bl,
      "interests":ints,"skills":sk,"skills_to_learn":learn,"short_term_goals":random.sample(gs,random.randint(1,min(2,len(gs)))),"long_term_goals":random.sample(gl,1),
      "languages":langs,"nearby_distance_km":random.choice([5,10,25,50]),"location":loc(),"opted_in_location_discovery":random.random()<.35,"email":None,**M})
    gt["users"][f"u{i:04d}"]={"primary":prim,"secondary":extra}

# ---------- interactions ----------
items=[("community",c["id"],gt["communities"][c["id"]]["primary"]) for c in communities]+[("event",e["id"],gt["events"][e["id"]]["primary"]) for e in events]+[("activity",a["id"],gt["activities"][a["id"]]["primary"]) for a in activities]
by_k=defaultdict(list)
for it in items: by_k[it[2]].append(it)
inter=[]
for u in users:
    g=gt["users"][u["id"]]; mine=[g["primary"]]+g["secondary"]; seen=set()
    for _ in range(random.randint(8,20)):
        on=random.random()<.72; it=random.choice(by_k[random.choice(mine) if on else random.choice(KEYS)])
        if it[1] in seen: continue
        seen.add(it[1])
        act=random.choices(["view","save","join_or_register","feedback_helpful"],[.45,.25,.2,.1])[0] if on else random.choices(["view","feedback_not_relevant","save"],[.7,.25,.05])[0]
        inter.append({"user_id":u["id"],"item_type":it[0],"item_id":it[1],"action":act,"days_ago":random.randint(0,90),**M})
random.shuffle(inter)

# ---------- evaluation queries (English, Marathi, Hinglish) ----------
TPL=["I want to get better at {g}","Find people who are into {g}","Looking for a {g} group near me","Help me start with {g}"]
def rel_for(qc):
    rel={}
    for x,key in [(y,"communities") for y in communities]+[(y,"events") for y in events]+[(y,"activities") for y in activities]:
        m=gt[key][x["id"]]; p=m["primary"]; s=m["secondary"]
        if p in qc: rel[x["id"]]=2
        elif s in qc or any(p in K[q][7] for q in qc): rel[x["id"]]=1
    return rel
queries=[]
def addq(text,cl,kind,l):
    queries.append({"id":"","query":text,"query_type":kind,"language":l,"expected_clusters":cl,"relevance":rel_for(cl),"split":random.choices(["dev","test"],[.7,.3])[0],
      "labelling":"topic-cluster rule; relevance 2 = same topic, 1 = related topic (partial). Not produced by any model under test.",**M})
for k in KEYS:
    h=K[k][5]; addq(h[0],[k],"keyword","en"); addq(h[1],[k],"paraphrase","en"); addq(h[2],[k],"paraphrase","en")
    for t in random.sample(TPL,2): addq(t.format(g=K[k][6]),[k],"template","en")
    addq(Q_MR[k],[k],"marathi","mr"); addq(Q_HI[k],[k],"hinglish","hi-latn")
for j in range(40):
    a,b=random.sample(KEYS,2)
    if j<25: addq(f"I want to learn {K[a][6]} and also get into {K[b][6]}",[a,b],"multi_intent","en")
    elif j<33: addq(f"Mujhe {K[a][6]} aur {K[b][6]} dono seekhna hai",[a,b],"multi_intent","hi-latn")
    else: addq(f"मला {TOPIC_MR[a]} आणि {TOPIC_MR[b]} दोन्ही शिकायचे आहे",[a,b],"multi_intent","mr")
random.shuffle(queries)
for i,q in enumerate(queries,1): q["id"]=f"q{i:04d}"

def dump(name,data):
    with open(os.path.join(OUT,name),"w",encoding="utf-8") as f: f.write("[\n"+",\n".join(json.dumps(r,ensure_ascii=False) for r in data)+"\n]\n")
dump("synthetic_communities.json",communities); dump("synthetic_events.json",events); dump("synthetic_activities.json",activities)
dump("synthetic_users.json",users); dump("synthetic_interactions.json",inter); dump("eval_queries.json",queries)
json.dump(gt,open(os.path.join(OUT,"ground_truth_topics.json"),"w",encoding="utf-8"),ensure_ascii=False)

# ---------- taxonomy extension ----------
ext_i={"Culture and Arts":["Kabaddi and Kho-Kho","Kushti and Wrestling","Marathi Literature","Theatre and Drama","Indian Classical Music","Folk Dance","Handicrafts and Rangoli","Ganeshotsav and Festivals"],
 "Outdoors":["Fort Trekking"],"Learning":["Competitive Exam Prep (MPSC/UPSC)"],"Business":["Agriculture and AgriTech"],"Lifestyle":["Maharashtrian Cooking"]}
ext_s=["Acting","Classical Vocal","Tabla","Dance"]
base=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","align_dataset","taxonomy.json")
tax=json.load(open(base,encoding="utf-8")) if os.path.exists(base) else {"_note":"base taxonomy not found; extension only"}
tax["_note"]="Reference option lists. Not user data. Safe for production. v3 adds Maharashtra topics."
for g,l in ext_i.items(): tax.setdefault("interests",{}).setdefault(g,[]); tax["interests"][g]=list(dict.fromkeys(tax["interests"][g]+l))
tax.setdefault("skills",{}).setdefault("Arts",[]); tax["skills"]["Arts"]=ext_s
tax["languages"]=["Marathi","Hindi","English"]+[x for x in tax.get("languages",[]) if x not in ("Marathi","Hindi","English")]+["Konkani"]
tax["cities_maharashtra"]=CN
json.dump(tax,open(os.path.join(OUT,"taxonomy_maharashtra.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)

# verify every interest/skill used exists in taxonomy
ti={x for v in tax["interests"].values() for x in v}; ts={x for v in tax["skills"].values() for x in v}
mi={i for r in communities+events+activities+users for i in r["interests"]}; ms={s for r in communities for s in r.get("skills_supported",[])}|{s for r in events for s in r["skills"]}|{s for r in activities for s in r["skills_developed"]}|{s for r in users for s in r["skills"]+r["skills_to_learn"]}
print({"communities":len(communities),"events":len(events),"activities":len(activities),"users":len(users),"interactions":len(inter),"eval_queries":len(queries),"clusters":len(KEYS)})
print("interests not in taxonomy:",sorted(mi-ti)); print("skills not in taxonomy:",sorted(ms-ts))
print("empty-relevance queries:",sum(1 for q in queries if not q["relevance"]),"| median relevant/query:",statistics.median(len(q["relevance"]) for q in queries))
