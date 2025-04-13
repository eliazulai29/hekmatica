// CritiqueAnswer: Verify the answer's quality and identify missing information if any
class Critique {
  is_good bool
  missing_info string
  template_followed bool @description("Whether the answer follows the required template structure")
  section_feedback map<string, string> @description("Feedback on each section of the template")
  improvement_suggestions string[] @description("List of specific suggestions for improvement")
}

function CritiqueAnswer(question: string, answer: string) -> Critique {
  client CustomGPT4oMini

  prompt #"""
  You are a critical evaluator of the assistant's answer.
  
  Evaluate the answer against both the question and the required template:
  1. Does it have an Executive Summary (1-2 sentences)?
  2. Does it include a Detailed Explanation?
  3. Does it list 3-5 Key Points?
  4. Does it include proper citations in the full answer?
  
  If all template sections are present AND the answer addresses the question fully, set is_good to true.
  Otherwise, set is_good to false and provide:
  - missing_info: what information is missing (as a search query)
  - template_followed: whether the template structure was followed
  - section_feedback: specific feedback on each section
  - improvement_suggestions: specific actions to improve the answer
  
  Question: "{{ question }}"
  Answer: "{{ answer }}"
  
  {{ ctx.output_format }}
"""#
}

// Tests for CritiqueAnswer
test critique_complete_answer {
  functions [CritiqueAnswer]
  args { 
    question "What is 2+2?", 
    answer "2+2 is 4." 
  }
  @@assert({{ this.is_good == true }})
  @@assert({{ this.missing_info == "" }})
}

test critique_incomplete_answer {
  functions [CritiqueAnswer]
  args { 
    question "What are the benefits and risks of Bitcoin?", 
    answer "Bitcoin's benefits include decentralization and fast transactions." 
  }
  // The answer did not cover risks, expect critique to flag missing info about risks
  @@assert({{ this.is_good == false }})
  @@assert({{ "risk" in this.missing_info | lower() }})
}

test critique_incomplete_general_answer {
  functions [CritiqueAnswer]
  args { 
    question "Describe the water cycle, including evaporation and precipitation.", 
    answer "The water cycle involves water evaporating from the surface due to heat." 
  }
  // The answer only mentioned evaporation, not precipitation. Expect critique to flag missing info about precipitation.
  @@assert({{ this.is_good == false }})
  @@assert({{ "precipitation" in this.missing_info | lower() or "rainfall" in this.missing_info | lower() }})
}

// New tests for template validation
test critique_fully_templated_answer {
  functions [CritiqueAnswer]
  args { 
    question "What are the health benefits of regular exercise?", 
    answer "## Executive Summary\nRegular exercise provides numerous health benefits including improved cardiovascular health, weight management, and mental wellbeing.\n\n## Detailed Explanation\nExercise improves cardiovascular health by strengthening the heart muscle and improving circulation [0]. Regular physical activity helps maintain a healthy weight by burning calories and building muscle mass [1]. Additionally, exercise triggers the release of endorphins, which reduce stress and improve mood [2].\n\n## Key Points\n- Improves cardiovascular health and reduces risk of heart disease\n- Helps maintain healthy weight and metabolism\n- Enhances mental health by reducing stress and anxiety\n- Strengthens muscles and bones\n- Increases overall energy levels\n\n## Complete Answer\nRegular exercise provides numerous health benefits across multiple body systems [0]. When you exercise consistently, your heart becomes stronger and more efficient at pumping blood, which improves overall circulation and reduces the risk of heart disease [1]. Physical activity also helps in maintaining a healthy weight by burning calories and increasing your metabolic rate [2]. From a mental health perspective, exercise releases endorphins that act as natural mood elevators, reducing stress, anxiety, and symptoms of depression [3]." 
  }
  // The answer follows the template structure but has citation issues
  @@assert({{ this.is_good == false }})
  @@assert({{ this.template_followed == true }})
  @@assert({{ this.section_feedback | length > 0 }})
  @@assert({{ "citation" in this.missing_info | lower() or "reference" in this.missing_info | lower() }})
}

test critique_missing_template_sections {
  functions [CritiqueAnswer]
  args { 
    question "How does solar energy work?", 
    answer "Solar energy works by converting sunlight into electricity. Photovoltaic cells in solar panels contain semiconductor materials that generate an electric current when exposed to sunlight. This electricity can then be used to power homes and businesses." 
  }
  // The answer contains correct information but doesn't follow the template structure
  @@assert({{ this.is_good == false }})
  @@assert({{ this.template_followed == false }})
  @@assert({{ this.section_feedback | length > 0 }})
  @@assert({{ this.improvement_suggestions | length > 0 }})
}

test critique_template_with_missing_content {
  functions [CritiqueAnswer]
  args { 
    question "What are the main causes and effects of climate change?", 
    answer "## Executive Summary\nClimate change is primarily caused by human activities that release greenhouse gases into the atmosphere.\n\n## Detailed Explanation\nHuman activities such as burning fossil fuels, deforestation, and industrial processes release greenhouse gases like carbon dioxide and methane into the atmosphere [0]. These gases trap heat and cause global temperatures to rise.\n\n## Key Points\n- Burning fossil fuels releases CO2\n- Deforestation reduces carbon absorption\n- Industrial processes contribute to greenhouse gas emissions\n\n## Complete Answer\nClimate change is caused by the release of greenhouse gases from human activities [0]. When we burn fossil fuels for energy, transportation, and industrial processes, we release carbon dioxide into the atmosphere [1]. Deforestation reduces the Earth's ability to absorb carbon dioxide [2]." 
  }
  // The answer follows the template but doesn't address the effects of climate change
  @@assert({{ this.is_good == false }})
  @@assert({{ this.template_followed == true }})
  @@assert({{ "effects" in this.missing_info | lower() or "impact" in this.missing_info | lower() }})
  @@assert({{ this.improvement_suggestions | length > 0 }})
}

test critique_improper_citations {
  functions [CritiqueAnswer]
  args { 
    question "What are the differences between renewable and non-renewable energy sources?", 
    answer "## Executive Summary\nRenewable energy sources naturally replenish over time, while non-renewable sources are finite and will eventually be depleted.\n\n## Detailed Explanation\nRenewable energy sources include solar, wind, hydro, geothermal, and biomass energy. These sources naturally replenish within a human lifetime. Non-renewable energy sources include fossil fuels like coal, oil, and natural gas, which take millions of years to form and are being consumed much faster than they can be created.\n\n## Key Points\n- Renewable sources naturally replenish; non-renewable sources don't\n- Renewable energy typically produces fewer emissions\n- Non-renewable sources currently dominate global energy production\n- Renewable energy technology is rapidly advancing\n\n## Complete Answer\nThe fundamental difference between renewable and non-renewable energy sources is their rate of replenishment. Renewable energy sources can be replenished within a human lifetime, while non-renewable sources take millions of years to form. Solar energy harnesses the power of the sun, while fossil fuels like coal and oil are formed from ancient organic matter. Renewable energy typically produces fewer greenhouse gas emissions compared to non-renewable sources." 
  }
  // The answer follows the template structure but lacks proper citations
  @@assert({{ this.is_good == false }})
  @@assert({{ this.template_followed == true }})
  @@assert({{ "citation" in this.section_feedback["Complete Answer"] | lower() }})
  @@assert({{ this.improvement_suggestions | length > 0 }})
}
