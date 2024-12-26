from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from pydantic import BaseModel
from typing import List
import json
import re
from src.helper import llm_chain
from src.data_util import read_input_file
from src.logger import logging

# Khởi tạo ứng dụng FastAPI
app = FastAPI()


# Định nghĩa model cho request
class Choice(BaseModel):
    choiceText: str
    isCorrected: int


class QuestionResponse(BaseModel):
    questionText: str
    choices: List[Choice]
    difficultyLevel: str


def extract_correct_answers(text: str) -> list[str]:
    """
    Extracts all correct answer letters from the response text, handling both quoted and unquoted answers
    """
    # Pattern matches:
    # 1. Correct: followed by optional whitespace
    # 2. Optional quotes around the letter
    # 3. Single letter A, B, C, or D
    pattern = r'Correct:\s*\"?([ABCD])\"?'
    matches = re.findall(pattern, text)
    return matches


@app.post("/generate_mcqs/", response_model=List[QuestionResponse])
async def generate_mcqs(
        file: UploadFile = File(...),
        number: int = Form(...),
        difficulty: str = Form("easy")
):
    try:
        # Read the file content from the uploaded file (in bytes)
        file_content = await file.read()

        # Check if the file has content
        if not file_content:
            raise HTTPException(status_code=400, detail="No content in the uploaded file.")

        # Process the file content
        data = read_input_file(file_content)

        if not data:
            raise ValueError("File content could not be processed.")

        # Call the model to generate questions
        response = llm_chain.run(
            number=number,
            difficulty=difficulty,
            text=data
        )

        if not response:
            raise ValueError("No questions generated from the model.")

        # Log the success of MCQ generation
        logging.info('MCQs are generated successfully.')
        print(response)
        logging.debug(f"Generated Response: {response}")

        # Extract all correct answers first
        correct_answers = extract_correct_answers(response)
        if not correct_answers:
            raise ValueError("No correct answers found in the response")

        # Split response into questions
        questions = response.split("\n\n")
        questions_data = []
        correct_answer_index = 0

        for i in range(0, len(questions), 3):
            if correct_answer_index >= len(correct_answers):
                break

            question_text = questions[i].strip().replace('1.', '').replace('2.', '').replace('3.', '').replace('4.',
                                                                                                               '').replace(
                '5.', '')
            answer_block = questions[i + 1].strip()

            # Get the correct answer for this question
            correct_answer = correct_answers[correct_answer_index]
            correct_answer_index += 1

            # Clean up the question text
            question_text = question_text.replace('"', '').strip()

            choices = []
            correct_answer_found = False

            # Loop through options A, B, C, D and check if the choice matches the correct answer
            for option in ['A', 'B', 'C', 'D']:
                choice_text = ""
                if f"{option}." in answer_block:
                    choice_text = answer_block.split(f"{option}.")[1].split("\n")[0].strip().replace('"', '')

                # Mark the correct answer based on the extracted correct answer
                is_correct = 1 if correct_answer == option else 0
                if is_correct == 1:
                    correct_answer_found = True

                choices.append(Choice(
                    choiceText=f"<p>{option}. {choice_text}</p>",
                    isCorrected=is_correct
                ))

            # Log if no correct answer was found for a question
            if not correct_answer_found:
                logging.warning(f"No correct answer found for question: {question_text}")

            questions_data.append(QuestionResponse(
                questionText=f"<p>{question_text}</p>",
                choices=choices,
                difficultyLevel=difficulty
            ))

        if not questions_data:
            raise ValueError("No questions were processed.")

        return questions_data

    except ValueError as ve:
        logging.error(f"ValueError: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))

    except Exception as e:
        logging.error(f"Error generating MCQs: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while processing the file: {str(e)}")