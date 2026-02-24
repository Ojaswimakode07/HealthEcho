// Mock API for medical advice
export async function getMedicalAdvice(query) {
  // Simulate network delay
  await new Promise(resolve => setTimeout(resolve, 1500));

  // Medical responses based on keywords
  const responses = {
    headache: {
      result: "Based on your description of headache symptoms, here's some general information:\n\n• Common causes include tension, dehydration, lack of sleep, or eye strain\n• Over-the-counter pain relievers like ibuprofen or acetaminophen may help\n• Rest in a quiet, dark room and stay hydrated\n\n⚠️ Seek immediate medical attention if you experience: sudden severe headache, headache with fever/stiff neck, headache after head injury, or headache with confusion/speech problems.",
      recommendations: "Rest, hydration, OTC pain relievers. Consult a doctor if symptoms persist beyond 48 hours."
    },
    fever: {
      result: "Regarding fever symptoms:\n\n• Rest and stay hydrated\n• Use fever-reducing medications like acetaminophen or ibuprofen as directed\n• Monitor temperature regularly\n• Use a cool compress for comfort\n\n🚨 Emergency signs: fever over 103°F (39.4°C), difficulty breathing, severe headache, rash, confusion, persistent vomiting.",
      recommendations: "Monitor temperature every 4 hours, stay hydrated, rest. Seek medical care if fever persists >3 days."
    },
    cough: {
      result: "For cough symptoms:\n\n• Stay hydrated with warm fluids\n• Use honey for cough (if over 1 year old)\n• Try over-the-counter cough suppressants for dry cough\n• Use humidifier or steam inhalation\n\n⚠️ See a doctor if you have: coughing up blood, shortness of breath, fever over 100.4°F (38°C) for more than 3 days, or chest pain.",
      recommendations: "Warm fluids, rest, monitor breathing. Medical attention if breathing difficulties occur."
    },
    cold: {
      result: "For common cold symptoms:\n\n• Rest and stay hydrated\n• Use saline nasal spray for congestion\n• Warm fluids like tea with honey can soothe throat\n• Over-the-counter cold medications may help symptoms\n\nMost colds resolve within 7-10 days. See a doctor if symptoms worsen or persist.",
      recommendations: "Rest, hydration, symptomatic treatment. Monitor for fever or breathing difficulties."
    },
    stomach: {
      result: "For stomach discomfort:\n\n• Stay hydrated with clear fluids\n• Eat bland foods (BRAT diet: bananas, rice, applesauce, toast)\n• Avoid spicy, fatty, or dairy foods\n• Rest and apply heat pad for cramps\n\n⚠️ Seek medical attention for: severe pain, bloody stools, persistent vomiting, or dehydration signs.",
      recommendations: "Clear liquids, bland diet, rest. Medical attention if severe or persistent."
    },
    allergy: {
      result: "For allergy symptoms:\n\n• Antihistamines like cetirizine or loratadine may help\n• Use saline nasal rinse for congestion\n• Avoid known allergens when possible\n• Keep windows closed during high pollen days\n\nSee an allergist if symptoms are severe or persistent.",
      recommendations: "Antihistamines, allergen avoidance. Consult allergist for persistent symptoms."
    },
    default: {
      result: "I understand you're seeking medical information. While I can provide general guidance, please remember:\n\n• This information is for educational purposes only\n• Always consult with healthcare professionals for medical advice\n• In emergencies, call your local emergency number immediately\n\nCould you provide more specific details about your symptoms? This will help me give you more relevant information.",
      recommendations: "Please provide more specific details about your symptoms for personalized guidance."
    }
  };

  const queryLower = query.toLowerCase();
  
  if (queryLower.includes("headache") || queryLower.includes("head pain")) 
    return responses.headache;
  if (queryLower.includes("fever") || queryLower.includes("temperature")) 
    return responses.fever;
  if (queryLower.includes("cough") || queryLower.includes("coughing")) 
    return responses.cough;
  if (queryLower.includes("cold") || queryLower.includes("flu") || queryLower.includes("sneeze")) 
    return responses.cold;
  if (queryLower.includes("stomach") || queryLower.includes("nausea") || queryLower.includes("vomit") || queryLower.includes("diarrhea")) 
    return responses.stomach;
  if (queryLower.includes("allergy") || queryLower.includes("allergic") || queryLower.includes("pollen")) 
    return responses.allergy;

  return responses.default;
}

export async function api(endpoint, data) {
  // Mock API for authentication
  await new Promise(resolve => setTimeout(resolve, 800));
  
  return { success: true };
}