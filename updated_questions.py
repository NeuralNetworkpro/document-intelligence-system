# Updated questions based on analysis of the 24 OCR documents for FLAVOUR ORANGE 

# NUTRIENT_QUESTIONS - Based on actual nutritional data found in Document 14
NUTRIENT_QUESTIONS = [
    "What is the Energy content in KJ/100g?",
    "What is the Energy content in K Cal/100g?", 
    "What is the Total Carbohydrate content per 100g?",
    "What is the Sugar content per 100g?",
    "What is the Starch content per 100g?",
    "What is the Protein content per 100g?",
    "What is the Total Fat content per 100g?",
    "What is the Saturated Fat content per 100g?",
    "What is the Trans Fat content per 100g?",
    "What is the Dietary Fiber content per 100g?",
    "What is the Sodium content in mg/100g?",
    "What is the Organic Acid content per 100g?",
    "What is the Moisture content per 100g?",
    "What is the Polyols content per 100g?",
    "What is the Cholesterol content in mg/100g?"
]

# DIETARY_QUESTIONS - Based on actual certifications and statements found
DIETARY_QUESTIONS = [
    "Is the ingredient Halal certified? (Yes/No/Unknown)",
    "Is the ingredient Kosher certified? (Yes/No/Unknown)", 
    "Is the ingredient Porcine-free? (Yes/No/Unknown)",
    "Is the ingredient Alcohol-free? (Yes/No/Unknown)",
    "Is the ingredient Gluten-free? (Yes/No/Unknown)",
    "Is the ingredient classified as Natural flavoring? (Yes/No/Unknown)",
    "Is the ingredient Latex-free? (Yes/No/Unknown)",
    "Does the ingredient contain any artificial flavors? (Yes/No/Unknown)",
    "Does the ingredient contain any artificial colors? (Yes/No/Unknown)",
    "Is the ingredient suitable for Vegan consumption? (Yes/No/Unknown)"
]

# ALLERGEN_QUESTIONS - Based on actual allergen declarations found in documents
ALLERGEN_QUESTIONS = [
    "Does the ingredient contain Cereals containing gluten and products thereof?",
    "Does the ingredient contain Crustaceans and products thereof?", 
    "Does the ingredient contain Eggs and products thereof?",
    "Does the ingredient contain Fish and products thereof?",
    "Does the ingredient contain Peanuts and products thereof?",
    "Does the ingredient contain Soybeans and products thereof?",
    "Does the ingredient contain Milk and products thereof?",
    "Does the ingredient contain Tree nuts and products thereof?",
    "Does the ingredient contain Celery and products thereof?",
    "Does the ingredient contain Mustard and products thereof?",
    "Does the ingredient contain Sesame seeds and products thereof?",
    "Does the ingredient contain Sulphur dioxide and sulphites at concentration ≥10 mg/kg?",
    "Does the ingredient contain Lupin and products thereof?",
    "Does the ingredient contain Molluscs and products thereof?",
    "Does the ingredient contain Latex?",
    "Are there any added sulphites in concentration ≥10 mg/kg?",
    "Is there risk of cross-contamination with any major allergens?"
]

# GMO_QUESTIONS - Based on actual GMO statements and evaluations found
GMO_QUESTIONS = [
    "Is the ingredient manufactured from genetically modified ingredients? (Yes/No)",
    "Does the ingredient fall under EU regulations (EC) 1829/2003 and 1830/2003? (Yes/No)",
    "Does the ingredient require GMO labeling according to FSANZ Food Standard 1.5.2? (Yes/No)",
    "Does the ingredient contain novel DNA/protein in the final product? (Yes/No)",
    "Is there risk of GMO cross-contamination during manufacturing? (Yes/No)",
    "Are any GMO ingredients used in the manufacturing facility? (Yes/No)",
    "Is the ingredient classified as Non-GM? (Yes/No)"
]

# SAFETY_QUESTIONS - New category based on safety statements found
SAFETY_QUESTIONS = [
    "Has the ingredient been tested for Heavy Metals? (Yes/No)",
    "Does the ingredient comply with Heavy Metal specifications (As ≤3ppm, Pb ≤10ppm, Cd ≤1ppm, Hg ≤1ppm)? (Yes/No)",
    "Has the ingredient been subjected to irradiation treatment? (Yes/No)",
    "Is the ingredient free from Melamine contamination? (Yes/No)",
    "Does the ingredient comply with pesticide residue regulations? (Yes/No)",
    "Is the ingredient free from BSE/TSE risk materials? (Yes/No)",
    "Does the ingredient contain any residual solvents? (Yes/No)",
    "Is the ingredient free from PAH (Polycyclic Aromatic Hydrocarbons)? (Yes/No)"
]

# COMPOSITION_QUESTIONS - New category based on ingredient declarations found
COMPOSITION_QUESTIONS = [
    "What percentage of Natural Flavorings does the ingredient contain?",
    "What percentage of Corn Syrup Solids does the ingredient contain?",
    "What percentage of Maltose does the ingredient contain?",
    "What percentage of Starches does the ingredient contain?",
    "What is the concentration of Tocopherols in the ingredient?",
    "Does the ingredient contain Maltodextrin? (Yes/No)",
    "Does the ingredient contain Starch Sodium Octenyl Succinate? (Yes/No)",
    "What are the main carrier components in the ingredient?",
    "What is the moisture content specification range?",
    "What is the particle size range specification?"
]

# MICROBIOLOGICAL_QUESTIONS - New category based on CoA microbiological data
MICROBIOLOGICAL_QUESTIONS = [
    "What is the Standard Plate Count specification range?",
    "What is the Yeast & Mold count specification?",
    "Is Salmonella detected in 25g of the ingredient? (Yes/No)",
    "What is the Coliform count specification?",
    "Is Staphylococcus Aureus detected in the ingredient? (Yes/No)",
    "Does the ingredient meet microbiological safety standards? (Yes/No)",
    "What is the shelf life of the ingredient?",
    "What are the recommended storage conditions?"
]

# REGULATORY_QUESTIONS - New category based on regulatory compliance documents
REGULATORY_QUESTIONS = [
    "Does the ingredient comply with EU Food Grade requirements? (Yes/No)",
    "Is the ingredient classified as a Novel Food according to EU regulation 258/97? (Yes/No)",
    "Does the ingredient comply with Commission regulation (EC) 396/2005 on pesticide residues? (Yes/No)",
    "Does the ingredient comply with Commission regulation (EU) 1881/2006 on contaminants? (Yes/No)",
    "Is the ingredient registered according to REACH regulation 1907/2006? (Yes/No)",
    "Does the ingredient meet Indonesian BPOM regulations? (Yes/No)",
    "Is the ingredient approved for food use in target markets? (Yes/No)"
]