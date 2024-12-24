from fastapi import FastAPI, File, UploadFile, Form
from pydantic import BaseModel
from typing import List
import json
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

# API Endpoint để upload file và tạo MCQs
@app.post("/generate_mcqs/", response_model=List[QuestionResponse])
async def generate_mcqs(
        file: UploadFile = File(...),
        number: int = Form(...),
        difficulty: str = Form("easy")
):
    try:
        # Đọc nội dung file từ UploadFile (dữ liệu trả về là 'bytes')
        file_content = await file.read()

        # Truyền 'file_content' vào hàm đọc file mà không yêu cầu 'name'
        data = read_input_file(file_content)

        # Gọi mô hình để tạo câu hỏi
        response = llm_chain.run(
            number=number,
            difficulty=difficulty,
            text=data
        )

        if not response:
            raise ValueError("No questions generated from the model.")

        # Log quá trình tạo MCQs
        logging.info('MCQs are generated')

        # Xử lý response thành định dạng JSON
        questions_data = []

        # Giả sử response là chuỗi các câu hỏi, tách nhau bởi 2 dòng trống
        questions = response.split("\n\n")

        for i in range(0, len(questions), 3):  # Mỗi câu hỏi có 3 dòng
            question_text = questions[i].strip().replace('1.', '').replace('2.', '').replace('3.', '').replace('4.',
                                                                                                               '').replace(
                '5.', '')

            answer_block = questions[i + 1].strip()
            correct_answer = questions[i + 2].strip().replace('Correct:', '').strip()

            choices = []
            correct_answer_found = False  # Biến này dùng để kiểm tra nếu chúng ta tìm được đáp án đúng

            for option in ['A', 'B', 'C', 'D']:
                choice_text = ""
                if f"{option}." in answer_block:
                    choice_text = answer_block.split(f"{option}.")[1].split("\n")[0].strip()

                # Nếu đáp án chính xác là option, đánh dấu là đúng
                is_correct = 1 if correct_answer.strip().upper() == option else 0

                if is_correct == 1:
                    correct_answer_found = True

                choices.append({
                    "choiceText": f"<p>{option}. {choice_text}</p>",
                    "isCorrected": is_correct
                })

            # Nếu không tìm được câu trả lời đúng, có thể có vấn đề trong cách xác định câu trả lời
            if not correct_answer_found:
                logging.warning(f"No correct answer found for question: {question_text}")

            questions_data.append({
                "questionText": f"<p>{question_text}</p>",
                "choices": choices,
                "difficultyLevel": difficulty
            })

        if not questions_data:
            raise ValueError("No questions were processed.")

        return questions_data


    except Exception as e:
        logging.error(f"Error generating MCQs: {e}")
        return {"error": f"An error occurred while processing the file: {str(e)}"}
