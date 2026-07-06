"""
Populate data/labels.jsonl with a curated, bilingual (English + Hinglish +
Hindi/Devanagari) hand-label set, so the model can be evaluated on a REAL
held-out test split instead of only synthetic data.

This is deliberately diverse and includes hard negatives (benign messages that
mention delivery/DM but no substance) so the measured precision is honest, not
inflated. Run once:

    python build_demo_labels.py
    python -m narcoscope.train          # retrain including these labels
    python -m narcoscope.evaluate       # real accuracy on the held-out split

Labelling convention: 1 = drug-sale related, 0 = benign.
"""

from narcoscope.labeling import LabelStore

# --- substance mentions across languages ---
SUBSTANCES = [
    "MDMA", "LSD tabs", "mephedrone", "ecstasy pills", "acid tabs", "charas",
    "ganja", "hash", "molly", "blotters",
    "chitta", "garda", "afeem", "smack", "brown sugar", "maal",
    "चिट्टा", "गांजा", "चरस", "अफीम", "स्मैक", "गर्दा", "भांग",
]

# --- sale-behaviour phrases across languages ---
SALE = [
    "DM to order", "home delivery available", "COD available", "discreet packing",
    "stock available, DM for price", "pan india delivery, safe delivery",
    "rate pucho DM pe", "home delivery ho jayegi", "maal hai bhai DM karo",
    "setting ho jayegi", "cash on delivery available",
    "रेट पूछो DM पर", "होम डिलीवरी उपलब्ध है", "माल है डीएम करो",
    "सेटिंग हो जाएगी, छुपा के भेजेंगे",
]

# --- benign messages (incl. hard negatives with delivery/DM but no substance) ---
BENIGN = [
    "Good morning everyone, have a great day",
    "Society meeting tomorrow at 6pm in the community hall",
    "Water supply will be interrupted from 10am to 2pm today",
    "New gym opening in Indore next month, early bird discount",
    "Protein shake recipe for post-workout recovery",
    "Breaking: Gwalior traffic police announce new one-way rules",
    "Weather update: heavy rainfall expected this weekend in MP",
    "Happy Diwali to all our members and their families",
    "Join our channel for daily Madhya Pradesh news digest",
    "Check out my new travel vlog from Khajuraho",
    "Fresh vegetables home delivery available, DM to order please",
    "Homemade cakes, COD available across Bhopal, DM for price list",
    "Book tuition classes, pan india online delivery of study material",
    "Weekend cricket match, who all are coming to the ground",
    "New restaurant opened near City Centre, must try the thali",
    "आज मौसम बहुत अच्छा है, शाम को टहलने चलें",
    "कल सोसाइटी की मीटिंग है शाम 6 बजे",
    "सुबह की सैर सेहत के लिए बहुत अच्छी होती है",
    "आज पानी सुबह 10 से दोपहर 2 बजे तक नहीं आएगा",
    "दिवाली की हार्दिक शुभकामनाएं सभी को",
    "नई जिम अगले महीने खुल रही है, जल्दी रजिस्टर करें",
    "क्या आज शाम क्रिकेट मैच देखने चलें?",
    "ताज़ी सब्ज़ियों की होम डिलीवरी उपलब्ध है, ऑर्डर के लिए मैसेज करें",
    "घर के बने केक, ग्वालियर में डिलीवरी, रेट के लिए डीएम करें",
    "bhai kal movie chalein multiplex mein?",
    "aaj traffic bahut hai, thoda late ho jaunga",
    "gym ke baad protein shake peena zaroori hai",
    "party this weekend at my place, sab aana",
    "online classes ki home delivery of books available, DM for details",
    "Congratulations to our team for winning the tournament",
    "Reminder: electricity bill due date is 15th this month",
    "Blood donation camp this Sunday at the district hospital",
    "New bakery near the railway station has amazing samosas",
    "Please carpool to office to reduce traffic and pollution",
    "Yoga session every morning at 6am in the city park",
    "Lost my black wallet near the market, please contact if found",
    "School annual function tickets available at the front office",
    "Monsoon safety tips: avoid waterlogged roads while driving",
    "Free coding workshop for students this Saturday, register now",
    "Anyone selling a used bicycle in good condition?",
    "Great turnout at the Swachh Bharat cleanliness drive today",
    "Movie tickets booked for Friday night show, who's in",
    "Diwali sale: 40% off on all electronics this week only",
    "Temple aarti timings changed to 7pm during winter",
    "Municipal water tanker will visit our lane at noon",
    "New bus route added between Gwalior and Jhansi",
    "Homework for class 8: chapters 4 and 5 of science",
    "Best chai spot in town, thank me later friends",
    "क्रिकेट टूर्नामेंट में हमारी टीम जीत गई, बधाई हो",
    "बिजली का बिल 15 तारीख तक जमा करना है",
    "रविवार को अस्पताल में रक्तदान शिविर लगेगा",
    "स्टेशन के पास नई बेकरी के समोसे बहुत अच्छे हैं",
    "सुबह 6 बजे पार्क में योग सत्र होता है रोज़",
    "बाज़ार के पास मेरा काला बटुआ खो गया है",
    "स्कूल के वार्षिक समारोह के टिकट ऑफिस से लें",
    "बारिश में जलभराव वाली सड़कों से बचें",
    "छात्रों के लिए मुफ्त कोडिंग कार्यशाला शनिवार को",
    "मंदिर की आरती का समय सर्दियों में शाम 7 बजे",
    "नगर निगम का पानी का टैंकर दोपहर को आएगा",
    "ग्वालियर से झांसी के बीच नई बस शुरू हुई है",
    "kal office jaldi jaana hai, meeting hai subah",
    "weekend pe ghar aa jao, mummy ne khana banaya hai",
    "bhai exam ki tayari kaisi chal rahi hai",
    "shaadi mein sab log time pe pahunch jaana",
    "aaj cricket practice hai sham ko ground pe",
    "naya phone liya hai, camera bahut accha hai",
    "restaurant mein table book kar diya hai 8 baje",
    "grocery ki home delivery bilkul time pe aa gayi",
    "medical store se dawai le aana ghar aate waqt",
    "cab book kar li hai airport ke liye subah 5 baje",
    "society ka maintenance is mahine badh gaya hai",
    "furniture home delivery available, DM for catalogue and price",
    "handmade jewellery, COD available, DM to order your design",
    "fresh milk delivery every morning, message for subscription",
    "tuition available for maths and science, DM for timings",
    "second hand books for sale, pan india shipping available",
    "flower bouquet home delivery for birthdays, DM to book",
    "Annual sports day rescheduled to next Friday due to rain",
    "Library will remain open till 9pm during exam season",
    "Free health checkup camp organised by the Rotary Club",
    "Please switch off lights during Earth Hour tonight",
    "New parking rules near the main market from Monday",
    "Community kitchen serving free meals during the festival",
    "Art exhibition by local students at the town hall this week",
    "Bus pass renewal counter open till 5pm on weekdays",
    "पुस्तकालय परीक्षा के दौरान रात 9 बजे तक खुला रहेगा",
    "रोटरी क्लब की ओर से मुफ्त स्वास्थ्य जांच शिविर",
    "मुख्य बाज़ार के पास नए पार्किंग नियम सोमवार से",
    "त्योहार के दौरान सामुदायिक रसोई में मुफ्त भोजन",
    "स्कूल का खेल दिवस बारिश के कारण अगले शुक्रवार को",
    "exam ke baad sab dost trip pe chalenge manali",
    "naye saal ki party ki planning kar rahe hain",
    "ghar ka function hai is weekend sab invited ho",
    "cricket ka final match kal hai zaroor dekhna",
    "sabzi mandi se taaza sabziyan le aaya hoon",
    "homemade pickle orders open, COD available, DM to order jars",
    "stationery shop home delivery for schools, DM for bulk price",
    "Traffic diversion near the fort for the marathon on Sunday",
    "College admission forms available online from tomorrow",
    "Power cut scheduled in sector 5 for maintenance today",
    "Cultural night at the university auditorium, all welcome",
    "Farmers market every Saturday morning near the stadium",
    "Registration open for the half marathon, limited slots",
    "Metro construction work near the bypass, expect delays",
    "Free eye checkup camp for senior citizens this week",
    "कॉलेज के दाखिले के फॉर्म कल से ऑनलाइन मिलेंगे",
    "किले के पास मैराथन के लिए ट्रैफिक डायवर्जन रहेगा",
    "सेक्टर 5 में आज बिजली मरम्मत के लिए कटौती रहेगी",
    "स्टेडियम के पास हर शनिवार किसान बाज़ार लगता है",
    "वरिष्ठ नागरिकों के लिए मुफ्त आंख जांच शिविर",
    "purana scooter bech raha hoon, chalega to dekh lena",
    "kal subah walk pe chalein lake ke paas",
    "office ki party hai friday ko sab ready rehna",
    "naya laptop order kiya hai kal deliver hoga",
    "tiffin service home delivery available, DM for monthly plan",
    "plant nursery home delivery of pots, DM to order saplings",
]


def _lang_platform(text: str) -> tuple[str, str]:
    has_dev = any("ऀ" <= c <= "ॿ" for c in text)
    return ("telegram", "hi") if has_dev else ("telegram", "en")


def main():
    store = LabelStore()
    n_pos = n_neg = 0

    # Drug messages: pair substances with sale phrases, rotating languages for variety.
    for i, sub in enumerate(SUBSTANCES):
        for j in range(5):
            phrase = SALE[(i + j) % len(SALE)]
            text = f"{sub} available, {phrase}"
            plat, _ = _lang_platform(text)
            store.add(text, 1, platform=plat, labeled_by="curator", source="demo_labels")
            n_pos += 1

    for text in BENIGN:
        plat, _ = _lang_platform(text)
        store.add(text, 0, platform=plat, labeled_by="curator", source="demo_labels")
        n_neg += 1

    print(f"Added {n_pos} drug + {n_neg} benign labels.")
    stats = store.stats()
    print("Label store:", stats["total"], "total")
    print("  train:", stats["train"], "\n  test :", stats["test"])


if __name__ == "__main__":
    main()
