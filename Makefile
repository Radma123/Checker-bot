build:
	docker build -t checker_bot .
run:
	docker run -d -v "C:\Users\Home_PC\Documents\GitHub\Checker-bot\setup":/app/setup checker_bot