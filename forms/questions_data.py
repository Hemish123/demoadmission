# SHREYAS FOUNDATION
# ACADEMIC YEAR 2027–28
# PARENTAL UNDERSTANDING & PARTNERSHIP QUESTIONNAIRE
# Total: 50 Marks (10 MCQs x 3 Marks = 30 Marks; 4 Written Questions x 5 Marks = 20 Marks)

# ==============================================================================
# 1. MCQ SCORING MATRIX (Questions 1 to 10)
# Each option (A, B, C, D) has a weighted score out of 3 marks as per official rubric.
# ==============================================================================
PARENT_MCQ_SCORING_MATRIX = {
    1: {"A": 1, "B": 3, "C": 2, "D": 1},
    2: {"A": 3, "B": 1, "C": 2, "D": 1},
    3: {"A": 2, "B": 1, "C": 3, "D": 1},
    4: {"A": 1, "B": 3, "C": 1, "D": 2},
    5: {"A": 3, "B": 1, "C": 3, "D": 1},
    6: {"A": 3, "B": 1, "C": 1, "D": 2},
    7: {"A": 3, "B": 1, "C": 1, "D": 3},
    8: {"A": 3, "B": 1, "C": 1, "D": 1},
    9: {"A": 3, "B": 1, "C": 2, "D": 1},
    10: {"A": 3, "B": 2, "C": 1, "D": 1},
}

# The single most philosophy-aligned answer for each MCQ (getting 3/3 marks)
ALIGNED_ANSWERS = {
    1: "B",
    2: "A",
    3: "C",
    4: "B",
    5: "A",  # Both A and C award 3 marks; primary is A
    6: "A",
    7: "A",  # Both A and D award 3 marks; primary is A
    8: "A",
    9: "A",
    10: "A",
}

# Written response question IDs (5 marks each, Q11 to Q14)
WRITTEN_QUESTION_IDS = [11, 12, 13, 14]
TOTAL_MCQ_MARKS = 30
TOTAL_WRITTEN_MARKS = 20
TOTAL_QUESTIONNAIRE_MARKS = 50

# Full questionnaire structure in English and Gujarati for Frontend / Mobile API delivery
QUESTIONNAIRE_QUESTIONS = [
    {
        "id": 1,
        "type": "mcq",
        "marks": 3,
        "focus": "Independence and age-appropriate support",
        "question_en": "Your child is trying to put on their shoes, but you are running late. What would you usually do?",
        "question_gu": "તમારું બાળક પોતાના જૂતા પહેરવાનો પ્રયત્ન કરી રહ્યું છે, પરંતુ તમારે મોડું થઈ રહ્યું છે. તમે સામાન્ય રીતે શું કરશો?",
        "options": [
            {"key": "A", "text_en": "Help immediately so the family stays on schedule.", "text_gu": "તરત જ મદદ કરશો જેથી કુટુંબ સમયસર પહોંચી શકે.", "score": 1},
            {"key": "B", "text_en": "Let the child try briefly, then offer only the help needed.", "text_gu": "બાળકને થોડો સમય પ્રયત્ન કરવા દેશો, પછી જેટલી જરૂર હોય તેટલી જ મદદ કરશો.", "score": 3},
            {"key": "C", "text_en": "Allow the child to finish independently even if it makes you late.", "text_gu": "મોડું થાય તો પણ બાળકને પોતાની જાતે જ પૂરું કરવા દેશો.", "score": 2},
            {"key": "D", "text_en": "Ask the child to practise later, when there is more time.", "text_gu": "જ્યારે વધુ સમય હોય ત્યારે બાળકને પ્રેક્ટિસ કરવા કહેશો.", "score": 1}
        ]
    },
    {
        "id": 2,
        "type": "mcq",
        "marks": 3,
        "focus": "Experiential learning and curiosity",
        "question_en": "Your child returns from school excited about planting seeds, but has no worksheet to show. What would you most want to know?",
        "question_gu": "તમારું બાળક શાળામાંથી બીજ વાવવા વિશે ઉત્સાહિત થઈને આવે છે, પરંતુ તેની પાસે બતાવવા માટે કોઈ વર્કશીટ નથી. તમે સૌથી વધુ શું જાણવા માંગશો?",
        "options": [
            {"key": "A", "text_en": "What the child noticed, tried and wondered about.", "text_gu": "બાળકે શું જોયું, શું અજમાવ્યું અને તેને કઈ બાબતની ઉત્સુકતા થઈ.", "score": 3},
            {"key": "B", "text_en": "Whether the activity will eventually help reading or science scores.", "text_gu": "શું આ પ્રવૃત્તિ ભવિષ્યમાં વાંચન કે વિજ્ઞાનના સ્કોરમાં મદદ કરશે.", "score": 1},
            {"key": "C", "text_en": "How the teacher will document the learning over time.", "text_gu": "શિક્ષક સમય જતાં આ શીખવાનું કેવી રીતે નોંધશે/દસ્તાવેજીકરણ કરશે.", "score": 2},
            {"key": "D", "text_en": "Whether the child completed the activity as instructed.", "text_gu": "શું બાળકે સૂચના મુજબ પ્રવૃત્તિ પૂર્ણ કરી હતી કે નહીં.", "score": 1}
        ]
    },
    {
        "id": 3,
        "type": "mcq",
        "marks": 3,
        "focus": "Individual pace; avoiding comparison",
        "question_en": "Another child of the same age can already read simple words; yours cannot. What is your likely first response?",
        "question_gu": "તે જ ઉંમરનું બીજું બાળક સરળ શબ્દો વાંચી શકે છે; તમારું બાળક હજી નથી વાંચી શકતું. તમારો પ્રથમ પ્રતિભાવ શું હોવાની શક્યતા છે?",
        "options": [
            {"key": "A", "text_en": "Ask the teacher whether there is any reason for concern and what support is appropriate.", "text_gu": "શિક્ષકને પૂછશો કે શું કોઈ ચિંતાનું કારણ છે અને કયો યોગ્ય ટેકો આપી શકાય.", "score": 2},
            {"key": "B", "text_en": "Start extra reading practice at home immediately.", "text_gu": "ઘરે તરત જ વધારાનું વાંચન શરૂ કરાવશો.", "score": 1},
            {"key": "C", "text_en": "Observe your child’s interests and development without comparing, while remaining open to guidance.", "text_gu": "સરખામણી કર્યા વગર બાળકના રસ અને વિકાસનું નિરીક્ષણ કરશો અને માર્ગદર્શન માટે ખુલ્લા રહેશો.", "score": 3},
            {"key": "D", "text_en": "Ask the school to introduce more formal reading lessons for everyone.", "text_gu": "બધા માટે વધુ ઔપચારિક વાંચન પાઠ શરૂ કરવા શાળાને વિનંતી કરશો.", "score": 1}
        ]
    },
    {
        "id": 4,
        "type": "mcq",
        "marks": 3,
        "focus": "Responsibility and practical life skills",
        "question_en": "Your child resists tidying up after play. What would you usually try first?",
        "question_gu": "રમ્યા પછી તમારું બાળક વસ્તુઓ ગોઠવવાની ના પાડે છે. તમે સામાન્ય રીતે પહેલા શું પ્રયાસ કરશો?",
        "options": [
            {"key": "A", "text_en": "Tidy up yourself to avoid an argument.", "text_gu": "વિવાદ ટાળવા માટે તમે જાતે જ ગોઠવી લેશો.", "score": 1},
            {"key": "B", "text_en": "Make it a shared activity and gradually give the child more responsibility.", "text_gu": "તેને સાથે મળીને કરવાની પ્રવૃત્તિ બનાવશો અને ધીમે ધીમે બાળકને વધુ જવાબદારી સોંપશો.", "score": 3},
            {"key": "C", "text_en": "Insist the child complete it alone before doing anything else.", "text_gu": "બીજું કંઈ પણ કરતા પહેલા બાળક પોતે જ પૂરું કરે તેવો આગ્રહ રાખશો.", "score": 1},
            {"key": "D", "text_en": "Leave the toys and return to the issue when everyone is calmer.", "text_gu": "રમકડાં ત્યાં જ રહેવા દેશો અને જ્યારે બધા શાંત થાય ત્યારે વાત કરશો.", "score": 2}
        ]
    },
    {
        "id": 5,
        "type": "mcq",
        "marks": 3,
        "focus": "Play-based learning and constructive dialogue",
        "question_en": "The school recommends fewer worksheets and more play-based exploration than you expected. What would you do?",
        "question_gu": "શાળા તમારી અપેક્ષા કરતાં ઓછી વર્કશીટ અને રમત આધારિત શિક્ષણની ભલામણ કરે છે. તમે શું કરશો?",
        "options": [
            {"key": "A", "text_en": "Ask teachers to explain how learning and progress are observed, then consider the approach.", "text_gu": "શિક્ષકોને પૂછશો કે શીખવાની અને પ્રગતિની નોંધ કેવી રીતે લેવાય છે, પછી તે અભિગમ સ્વીકારશો.", "score": 3},
            {"key": "B", "text_en": "Request additional worksheets for your child.", "text_gu": "તમારા બાળક માટે વધારાની વર્કશીટ્સની માંગ કરશો.", "score": 1},
            {"key": "C", "text_en": "Support the approach and discuss any specific concerns as they arise.", "text_gu": "આ અભિગમને સમર્થન આપશો અને કોઈપણ ચોક્કસ ચિંતા હોય તો ચર્ચા કરશો.", "score": 3},
            {"key": "D", "text_en": "Wait to see examination or test results before deciding whether it works.", "text_gu": "પરીક્ષાના પરિણામો જોયા પછી જ નક્કી કરશો કે આ પદ્ધતિ યોગ્ય છે કે નહીં.", "score": 1}
        ]
    },
    {
        "id": 6,
        "type": "mcq",
        "marks": 3,
        "focus": "Bilingual learning: English and Gujarati",
        "question_en": "Your family most often uses a language other than Gujarati or English at home. How would you support Shreyas’s emphasis on both English and Gujarati?",
        "question_gu": "તમારું કુટુંબ ઘરે મોટેભાગે ગુજરાતી કે અંગ્રેજી સિવાયની ભાષા બોલે છે. તમે શ્રેયસના અંગ્રેજી અને ગુજરાતી બંને પરના ભારને કેવી રીતે ટેકો આપશો?",
        "options": [
            {"key": "A", "text_en": "Encourage exposure to both through stories, conversations and school activities, even if we are not fluent.", "text_gu": "આપણે અસ્ખલિત ન હોઈએ તો પણ વાર્તાઓ, વાતચીત અને શાળાની પ્રવૃત્તિઓ દ્વારા બંને ભાષા સાથે જોડાણ કરાવીશું.", "score": 3},
            {"key": "B", "text_en": "Prioritise English because it will be most useful later.", "text_gu": "અંગ્રેજીને પ્રાથમિકતા આપીશું કારણ કે તે ભવિષ્યમાં વધુ ઉપયોગી થશે.", "score": 1},
            {"key": "C", "text_en": "Rely entirely on school to develop both languages.", "text_gu": "બંને ભાષાઓ શીખવવા માટે સંપૂર્ણપણે શાળા પર નિર્ભર રહીશું.", "score": 1},
            {"key": "D", "text_en": "Ask the school to focus on whichever language the child already knows best.", "text_gu": "બાળક જે ભાષા પહેલેથી સારી રીતે જાણે છે તેના પર જ ધ્યાન કેન્દ્રિત કરવા શાળાને કહીશું.", "score": 2}
        ]
    },
    {
        "id": 7,
        "type": "mcq",
        "marks": 3,
        "focus": "Child-led interests with safe guidance",
        "question_en": "Your child becomes deeply interested in insects and spends a long time observing them outdoors. What would you most likely do?",
        "question_gu": "તમારું બાળક જીવજંતુઓમાં ખૂબ રસ લે છે અને બહાર લાંબો સમય તેનું નિરીક્ષણ કરે છે. તમે મોટેભાગે શું કરશો?",
        "options": [
            {"key": "A", "text_en": "Encourage exploration while setting sensible safety and time boundaries.", "text_gu": "સુરક્ષા અને સમયની યોગ્ય મર્યાદા રાખીને સંશોધન માટે પ્રોત્સાહિત કરશો.", "score": 3},
            {"key": "B", "text_en": "Redirect the child toward an activity with clearer academic benefits.", "text_gu": "બાળકને શૈક્ષણિક રીતે વધુ ફાયદાકારક પ્રવૃત્તિ તરફ વાળશો.", "score": 1},
            {"key": "C", "text_en": "Let the interest continue without any adult involvement or limits.", "text_gu": "કોઈપણ વડીલની સંડોવણી કે મર્યાદા વિના તે રસ ચાલુ રહેવા દેશો.", "score": 1},
            {"key": "D", "text_en": "Use the interest as an opportunity to ask questions, draw or look for information together.", "text_gu": "પ્રશ્નો પૂછવા, ચિત્ર દોરવા કે સાથે મળીને માહિતી શોધવા માટે આ રસનો ઉપયોગ કરશો.", "score": 3}
        ]
    },
    {
        "id": 8,
        "type": "mcq",
        "marks": 3,
        "focus": "Social development and home–school cooperation",
        "question_en": "A teacher tells you your child is struggling to share materials with classmates. What would you do first?",
        "question_gu": "શિક્ષક જણાવે છે કે તમારું બાળક સહપાઠીઓ સાથે વસ્તુઓ વહેંચવામાં ખચકાટ અનુભવે છે. તમે પહેલા શું કરશો?",
        "options": [
            {"key": "A", "text_en": "Ask for examples and agree with the teacher on ways to support the child.", "text_gu": "ઉદાહરણો પૂછશો અને બાળકને ટેકો આપવાના રસ્તાઓ પર શિક્ષક સાથે સંમત થશો.", "score": 3},
            {"key": "B", "text_en": "Explain that children grow out of such behaviour and wait.", "text_gu": "સમજાવશો કે ઉંમર સાથે બાળકો શીખી જશે અને રાહ જોશો.", "score": 1},
            {"key": "C", "text_en": "Tell the child firmly that sharing is compulsory.", "text_gu": "બાળકને કડકાઈથી કહેશો કે વસ્તુ વહેંચવી ફરજિયાત છે.", "score": 1},
            {"key": "D", "text_en": "Ask the teacher to manage it entirely at school.", "text_gu": "શિક્ષકને વિનંતી કરશો કે શાળામાં જ તેનું નિરાકરણ કરે.", "score": 1}
        ]
    },
    {
        "id": 9,
        "type": "mcq",
        "marks": 3,
        "focus": "Holistic kindergarten expectations",
        "question_en": "Which statement best reflects what you expect from a kindergarten school?",
        "question_gu": "કયું વિધાન કિન્ડરગાર્ટન શાળા પાસેથી તમારી અપેક્ષાને શ્રેષ્ઠ રીતે પ્રતિબિંબિત કરે છે?",
        "options": [
            {"key": "A", "text_en": "A balance of curiosity, relationships, independence, play and foundational learning.", "text_gu": "જિજ્ઞાસા, સંબંધો, સ્વાયત્તતા/સ્વતંત્રતા, રમત અને પાયાના શિક્ષણનું સંતુલન.", "score": 3},
            {"key": "B", "text_en": "Clear academic targets and regular written evidence of achievement.", "text_gu": "સ્પષ્ટ શૈક્ષણિક લક્ષ્યો અને સિદ્ધિના નિયમિત લેખિત પુરાવા.", "score": 1},
            {"key": "C", "text_en": "A nurturing environment, with teachers explaining progress in varied ways.", "text_gu": "એક ઉછેરનું વાતાવરણ, જેમાં શિક્ષકો વિવિધ રીતે પ્રગતિ સમજાવે.", "score": 2},
            {"key": "D", "text_en": "Early preparation for competitive academic pathways.", "text_gu": "સ્પર્ધાત્મક શૈક્ષણિક માર્ગો માટે પ્રારંભિક તૈયારી.", "score": 1}
        ]
    },
    {
        "id": 10,
        "type": "mcq",
        "marks": 3,
        "focus": "Constructive communication and partnership",
        "question_en": "If you disagree with a school practice or receive feedback that requires a change at home, what would you usually do?",
        "question_gu": "જો તમે શાળાના કોઈ નિર્ણય સાથે અસંમત હોવ અથવા ઘરે ફેરફાર કરવાની જરૂર પડે તેવો અભિપ્રાય મળે, તો તમે શું કરશો?",
        "options": [
            {"key": "A", "text_en": "Raise the concern privately, listen to the reasoning and seek a workable solution.", "text_gu": "અંગત રીતે ચિંતા રજૂ કરશો, કારણ સમજશો અને વ્યવહારુ ઉકેલ શોધશો.", "score": 3},
            {"key": "B", "text_en": "Follow the school’s decision even if I remain uncomfortable.", "text_gu": "અસગવડ હોવા છતાં શાળાના નિર્ણયનું પાલન કરશો.", "score": 2},
            {"key": "C", "text_en": "Ask other parents first and jointly press for a change.", "text_gu": "પહેલા અન્ય વાલીઓને પૂછશો અને સંયુક્ત રીતે ફેરફાર માટે દબાણ કરશો.", "score": 1},
            {"key": "D", "text_en": "Expect the school to make an exception for my child.", "text_gu": "શાળા મારા બાળક માટે અપવાદ બનાવે તેવી અપેક્ષા રાખશો.", "score": 1}
        ]
    },
    # --------------------------------------------------------------------------
    # Written Questions (Q11 - Q14, 5 marks each)
    # --------------------------------------------------------------------------
    {
        "id": 11,
        "type": "written",
        "marks": 5,
        "focus": "Reflection on child’s real-life learning experience",
        "question_en": "Please describe one recent situation in which your child showed curiosity, frustration, independence or care for someone. What did you do, and what did your child learn from the experience?",
        "question_gu": "કૃપા કરીને તાજેતરની એક એવી પરિસ્થિતિનું વર્ણન કરો જેમાં તમારા બાળકે જિજ્ઞાસા, હતાશા, સ્વતંત્રતા અથવા કોઈના પ્રત્યે કાળજી દર્શાવી હોય. તમે શું કર્યું, અને બાળકે તે અનુભવમાંથી શું શીખ્યું?",
    },
    {
        "id": 12,
        "type": "written",
        "marks": 5,
        "focus": "Year-round support for underprivileged children",
        "question_en": "Shreyas Foundation believes in supporting underprivileged children throughout the year. In what practical ways could you and your family contribute time, skills, resources or participation to support these children and help sustain this initiative?",
        "question_gu": "શ્રેયસ ફાઉન્ડેશન આખું વર્ષ વંચિત બાળકોને સહાય કરવામાં માને છે. આ પહેલને ટેકો આપવા માટે તમે અને તમારું કુટુંબ કઈ વ્યવહારુ રીતે સમય, કૌશલ્ય, સંસાધનો અથવા સહભાગિતાનું યોગદાન આપી શકો?",
    },
    {
        "id": 13,
        "type": "written",
        "marks": 5,
        "focus": "Education, values, life skills, Gujarati and Sanskar",
        "question_en": "What does a meaningful education mean to you beyond marks and examination results? What values, life skills and abilities would you most like your child to develop? Please include how you see Gujarati language, culture and Sanskar contributing to your child’s growth.",
        "question_gu": "ગુણ અને પરીક્ષાના પરિણામોથી આગળ વધીને અર્થપૂર્ણ શિક્ષણ એટલે તમારા માટે શું? તમે તમારા બાળકમાં કયા મૂલ્યો, જીવન કૌશલ્યો અને ક્ષમતાઓ વિકસાવવા માંગો છો? ગુજરાતી ભાષા, સંસ્કૃતિ અને સંસ્કારો બાળકના વિકાસમાં કેવી રીતે ફાળો આપે છે તે જણાવો.",
    },
    {
        "id": 14,
        "type": "written",
        "marks": 5,
        "focus": "Parent’s role in school partnership",
        "question_en": "What kind of partnership would you like to build with Shreyas Foundation? How would you contribute to your child’s learning at home and work with educators if the school shares feedback or suggests a different approach?",
        "question_gu": "તમે શ્રેયસ ફાઉન્ડેશન સાથે કેવા પ્રકારની ભાગીદારી બનાવવા માંગો છો? તમે ઘરે બાળકના શિક્ષણમાં કેવી રીતે યોગદાન આપશો અને જો શાળા કોઈ અલગ અભિગમ સૂચવે તો શિક્ષકો સાથે કેવી રીતે સહયોગ કરશો?",
    }
]


def score_parent_questionnaire(
    answers: dict,
    use_ai: bool = True,
    child_name: str = "",
    standard: str = ""
) -> dict:
    """
    Evaluates parent questionnaire answers against official 2027-28 rubric:
    - 10 MCQs x 3 Marks = 30 Marks max
    - 4 Written Questions x 5 Marks = 20 Marks max (evaluated via GPT-4o AI service)
    Returns:
    {
        "mcq_score": float (0-30),
        "written_score": float (0-20),
        "total_score": float (0-50),
        "mcq_scaled_to_7": float (scaled for Part X),
        "breakdown": {q_id: {"selected": "...", "score": 3, "max": 3}},
        "written_responses": {q_id: "..."},
        "ai_evaluations": {q_id: {"score": 4.5, "feedback": "..."}}
    }
    """
    mcq_total = 0
    breakdown = {}
    written_responses = {}

    # Score MCQs 1 to 10
    for q_id in range(1, 11):
        q_key_str = str(q_id)
        selected_opt = answers.get(q_key_str) or answers.get(q_id)
        if selected_opt:
            selected_opt = str(selected_opt).strip().upper()

        opt_scores = PARENT_MCQ_SCORING_MATRIX.get(q_id, {})
        earned_mark = opt_scores.get(selected_opt, 0)
        mcq_total += earned_mark

        breakdown[q_id] = {
            "selected": selected_opt or "-",
            "earned_marks": earned_mark,
            "max_marks": 3,
            "best_option": ALIGNED_ANSWERS.get(q_id)
        }

    # Extract written answers (Q11 to Q14)
    for q_id in WRITTEN_QUESTION_IDS:
        q_key_str = str(q_id)
        resp_text = str(answers.get(q_key_str) or answers.get(q_id) or "").strip()
        written_responses[q_id] = resp_text

    # Evaluate written responses:
    # 1. First check if explicit educator/manual marks were passed
    manual_written_marks = answers.get("written_marks") or {}
    ai_evaluations = {}

    if any(manual_written_marks.get(str(qid)) is not None for qid in WRITTEN_QUESTION_IDS):
        written_total = 0.0
        for q_id in WRITTEN_QUESTION_IDS:
            m = manual_written_marks.get(str(q_id))
            if m is not None:
                written_total += min(max(float(m), 0.0), 5.0)
    elif use_ai:
        # 2. Use GPT-4o AI Evaluation Service
        from .ai_evaluation_service import evaluate_written_answers_with_ai
        ai_result = evaluate_written_answers_with_ai(
            written_responses=written_responses,
            child_name=child_name,
            standard=standard
        )
        written_total = float(ai_result.get("total_written_score", 0.0))
        ai_evaluations = ai_result.get("evaluations", {})
    else:
        # 3. Baseline heuristic fallback
        from .ai_evaluation_service import _fallback_heuristic_evaluation
        ai_result = _fallback_heuristic_evaluation(written_responses)
        written_total = float(ai_result.get("total_written_score", 0.0))
        ai_evaluations = ai_result.get("evaluations", {})

    total_questionnaire_score = round(mcq_total + written_total, 2)
    # Scaled to 7 for Part X background score (MCQ portion: 30 marks mapped to 7)
    mcq_scaled_to_7 = round((mcq_total / 30.0) * 7.0, 2)

    return {
        "mcq_score": mcq_total,
        "written_score": written_total,
        "total_score": total_questionnaire_score,
        "max_score": 50,
        "mcq_scaled_to_7": mcq_scaled_to_7,
        "breakdown": breakdown,
        "written_responses": written_responses,
        "ai_evaluations": ai_evaluations
    }
