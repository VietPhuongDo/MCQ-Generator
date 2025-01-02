from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from pydantic import BaseModel
from typing import List
import re
from src.helper import llm_chain
from src.logger import logging
from src.data_util import read_input_file

# Initialize FastAPI application
app = FastAPI()

# Define models for the MCQs
class Choice(BaseModel):
    choiceText: str
    isCorrected: int

class QuestionResponse(BaseModel):
    questionText: str
    choices: List[Choice]
    difficultyLevel: str

def extract_correct_answers(text: str) -> List[str]:
    pattern = r'Correct:\s*\"?([ABCD])\"?'
    return re.findall(pattern, text)

def clean_question_text(question: str) -> str:
    question = re.sub(r'\d+\.\s*', '', question)
    return re.sub(r'\*\*', '', question).strip()

@app.post("/generate_mcqs/", response_model=List[QuestionResponse])
async def generate_mcqs(
        file: UploadFile = File(...),
        number: int = Form(...),
        difficulty: str = Form("easy")
):
    try:
        # Read file content
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="No content in the uploaded file.")

        # Process file content
        data = read_input_file(file_content)
        if not data:
            raise ValueError("File content could not be processed.")

        # Generate questions using the LLM chain
        response = llm_chain.run(number=number, difficulty=difficulty, text=data)
        if not response:
            raise ValueError("No questions generated from the model.")

        # Extract questions and correct answers
        correct_answers = extract_correct_answers(response)
        questions = response.split("\n\n")
        questions_data = []
        correct_answer_index = 0

        for i in range(0, len(questions), 3):
            if correct_answer_index >= len(correct_answers):
                break

            question_text = clean_question_text(questions[i].strip())
            answer_block = questions[i + 1].strip()

            correct_answer = correct_answers[correct_answer_index]
            correct_answer_index += 1

            choices = []
            for option in ['A', 'B', 'C', 'D']:
                if f"{option}." in answer_block:
                    choice_text = answer_block.split(f"{option}.")[1].split("\n")[0].strip().replace('"', '')
                    is_correct = 1 if correct_answer == option else 0
                    choices.append(Choice(
                        choiceText=f"<p>{choice_text}</p>",
                        isCorrected=is_correct
                    ))

            questions_data.append(QuestionResponse(
                questionText=f"<p>{question_text}</p>",
                choices=choices,
                difficultyLevel=difficulty
            ))

        return questions_data

    except ValueError as ve:
        logging.error(f"ValueError: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))

    except Exception as e:
        logging.error(f"Error generating MCQs: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.post("/generate_mcqs_by_topic/", response_model=List[QuestionResponse])
async def generate_mcqs_by_topic(
        topic: str = Form(...),
        number: int = Form(...),
        difficulty: str = Form("easy")
):
    try:
        if not topic.strip():
            raise HTTPException(status_code=400, detail="Topic cannot be empty.")

        # Generate questions using the LLM chain
        response = llm_chain.run(
            number=number,
            difficulty=difficulty,
            text=f"The topic is: {topic}. Create questions based on this topic."
        )
        if not response:
            raise ValueError("No questions generated from the model.")

        # Extract questions and correct answers
        correct_answers = extract_correct_answers(response)
        questions = response.split("\n\n")
        questions_data = []
        correct_answer_index = 0

        for i in range(0, len(questions), 3):
            if correct_answer_index >= len(correct_answers):
                break

            question_text = clean_question_text(questions[i].strip())
            answer_block = questions[i + 1].strip()

            correct_answer = correct_answers[correct_answer_index]
            correct_answer_index += 1

            choices = []
            for option in ['A', 'B', 'C', 'D']:
                if f"{option}." in answer_block:
                    choice_text = answer_block.split(f"{option}.")[1].split("\n")[0].strip().replace('"', '')
                    is_correct = 1 if correct_answer == option else 0
                    choices.append(Choice(
                        choiceText=f"<p>{choice_text}</p>",
                        isCorrected=is_correct
                    ))

            questions_data.append(QuestionResponse(
                questionText=f"<p>{question_text}</p>",
                choices=choices,
                difficultyLevel=difficulty
            ))

        return questions_data

    except ValueError as ve:
        logging.error(f"ValueError: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))

    except Exception as e:
        logging.error(f"Error generating MCQs by topic: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
