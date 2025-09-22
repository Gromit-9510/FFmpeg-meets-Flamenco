from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import time
import requests
import yaml
import os
from pathlib import Path

from ..utils.env import get_submitter_platform


@dataclass
class FlamencoConfig:
	base_url: str
	token: str

@dataclass
class FlamencoAutoConfig:
	base_url: str
	token: str
	manager_name: str
	listen_port: int
	success: bool
	error_message: str = ""

def setup_flamenco_for_ffmpeg(flamenco_path: str) -> FlamencoAutoConfig:
	"""Flamenco를 FFmpeg Encoder와 호환되도록 설정합니다. (V3: 기존 Manager 설정 보존)"""
	try:
		# 기본 설정 로드
		config = load_flamenco_config(flamenco_path)
		if not config.success:
			return config
		
		# Flamenco 경로 설정
		flamenco_dir = Path(flamenco_path)
		
		# 호환성 확인 (기존 설정은 수정하지 않음)
		compatibility_status = _check_flamenco_compatibility_v3(flamenco_dir)
		
		# 1. FFmpeg 전용 Worker 설정만 생성 (Manager 설정은 건드리지 않음)
		worker_config_path = flamenco_dir / "ffmpeg-worker.yaml"
		_setup_ffmpeg_worker_config(worker_config_path)
		
		# 2. Custom job type 스크립트 생성
		scripts_dir = flamenco_dir / "scripts"
		scripts_dir.mkdir(exist_ok=True)
		_setup_ffmpeg_job_type(scripts_dir)
		
		# 3. FFmpeg 전용 폴더 구조 생성
		_setup_ffmpeg_structure(flamenco_dir)
		
		# 4. 호환성 테스트
		test_result = _test_flamenco_connection(config)
		
		config.success = True
		config.error_message = f"FFmpeg Encoder V3 호환 설정이 완료되었습니다.\n{compatibility_status}\n{test_result}"
		return config
		
	except Exception as e:
		return FlamencoAutoConfig(
			base_url="",
			token="",
			manager_name="",
			listen_port=8080,
			success=False,
			error_message=f"Flamenco V3 설정 오류: {str(e)}"
		)

def _check_flamenco_compatibility(flamenco_dir: Path) -> str:
	"""Flamenco 설정의 호환성을 확인합니다."""
	status_messages = []
	
	# Manager 설정 확인
	manager_config_path = flamenco_dir / "flamenco-manager.yaml"
	if manager_config_path.exists():
		try:
			with open(manager_config_path, 'r', encoding='utf-8') as f:
				config = yaml.safe_load(f)
			
			# FFmpeg 변수 확인
			if 'variables' in config and 'ffmpeg' in config['variables']:
				status_messages.append("✅ Manager에 FFmpeg 변수가 설정되어 있습니다.")
			else:
				status_messages.append("⚠️ Manager에 FFmpeg 변수가 없습니다. 추가합니다.")
		except Exception as e:
			status_messages.append(f"❌ Manager 설정 읽기 오류: {e}")
	else:
		status_messages.append("⚠️ Manager 설정 파일이 없습니다.")
	
	# Worker 설정 확인
	worker_config_path = flamenco_dir / "flamenco-worker.yaml"
	if worker_config_path.exists():
		try:
			with open(worker_config_path, 'r', encoding='utf-8') as f:
				config = yaml.safe_load(f)
			
			# FFmpeg 변수 확인
			if 'variables' in config and 'ffmpeg' in config['variables']:
				status_messages.append("✅ Worker에 FFmpeg 변수가 설정되어 있습니다.")
			else:
				status_messages.append("⚠️ Worker에 FFmpeg 변수가 없습니다. 추가합니다.")
		except Exception as e:
			status_messages.append(f"❌ Worker 설정 읽기 오류: {e}")
	else:
		status_messages.append("⚠️ Worker 설정 파일이 없습니다. 생성합니다.")
	
	# Scripts 디렉토리 확인
	scripts_dir = flamenco_dir / "scripts"
	if scripts_dir.exists():
		ffmpeg_compiler = scripts_dir / "ffmpeg-job-compiler.py"
		if ffmpeg_compiler.exists():
			status_messages.append("✅ FFmpeg 작업 컴파일러가 있습니다.")
		else:
			status_messages.append("⚠️ FFmpeg 작업 컴파일러가 없습니다. 생성합니다.")
	else:
		status_messages.append("⚠️ Scripts 디렉토리가 없습니다. 생성합니다.")
	
	return "\n".join(status_messages)

def _check_flamenco_compatibility_v3(flamenco_dir: Path) -> str:
	"""Flamenco V3 설정의 호환성을 확인합니다. (기존 Manager 설정은 건드리지 않음)"""
	status_messages = []
	
	# Manager 설정 확인 (읽기만 하고 수정하지 않음)
	manager_config_path = flamenco_dir / "flamenco-manager.yaml"
	if manager_config_path.exists():
		try:
			with open(manager_config_path, 'r', encoding='utf-8') as f:
				config = yaml.safe_load(f)
			
			# Manager가 실행 중인지 확인
			status_messages.append("✅ Manager 설정 파일이 존재합니다.")
			
			# FFmpeg 변수 확인 (수정하지 않음)
			if 'variables' in config and 'ffmpeg' in config['variables']:
				status_messages.append("✅ Manager에 FFmpeg 변수가 이미 설정되어 있습니다.")
			else:
				status_messages.append("ℹ️ Manager에 FFmpeg 변수가 없습니다. (V3에서는 별도 Worker 사용)")
		except Exception as e:
			status_messages.append(f"❌ Manager 설정 읽기 오류: {e}")
	else:
		status_messages.append("⚠️ Manager 설정 파일이 없습니다.")
	
	# FFmpeg 전용 Worker 설정 확인
	ffmpeg_worker_config_path = flamenco_dir / "ffmpeg-worker.yaml"
	if ffmpeg_worker_config_path.exists():
		status_messages.append("✅ FFmpeg 전용 Worker 설정이 존재합니다.")
	else:
		status_messages.append("ℹ️ FFmpeg 전용 Worker 설정이 없습니다. 생성합니다.")
	
	# Scripts 디렉토리 확인
	scripts_dir = flamenco_dir / "scripts"
	if scripts_dir.exists():
		ffmpeg_compiler = scripts_dir / "ffmpeg-encode.js"
		if ffmpeg_compiler.exists():
			status_messages.append("✅ FFmpeg 작업 컴파일러가 있습니다.")
		else:
			status_messages.append("ℹ️ FFmpeg 작업 컴파일러가 없습니다. 생성합니다.")
	else:
		status_messages.append("ℹ️ Scripts 디렉토리가 없습니다. 생성합니다.")
	
	return "\n".join(status_messages)

def _test_flamenco_connection(config: FlamencoAutoConfig) -> str:
	"""Flamenco 연결을 테스트합니다."""
	try:
		from requests import Session
		session = Session()
		session.headers.update({
			"Authorization": f"Bearer {config.token}",
			"Content-Type": "application/json",
		})
		
		# 간단한 API 호출 테스트
		r = session.get(f"{config.base_url}/api/v3/version", timeout=10)
		r.raise_for_status()
		
		version_info = r.json()
		return f"✅ Flamenco 연결 성공! 버전: {version_info.get('version', 'Unknown')}"
		
	except Exception as e:
		return f"❌ Flamenco 연결 실패: {e}"

def _setup_ffmpeg_worker_config(worker_config_path: Path) -> None:
	"""FFmpeg 전용 Worker 설정 파일을 생성합니다. (V3: 기존 Manager 설정은 건드리지 않음)"""
	try:
		# FFmpeg 전용 Worker 설정 생성
		ffmpeg_worker_config = {
			'manager_url': 'http://localhost:8080',
			'worker_name': 'ffmpeg-encoder-worker',
			'worker_tags': ['ffmpeg', 'video', 'encoding'],
			'variables': {
				'ffmpeg': {
					'values': [
						{'platform': 'windows', 'value': 'ffmpeg'},
						{'platform': 'linux', 'value': 'ffmpeg'},
						{'platform': 'darwin', 'value': 'ffmpeg'}
					]
				}
			},
			'job_types': ['ffmpeg-encode'],
			'capabilities': {
				'ffmpeg': True,
				'video_encoding': True,
				'gpu_encoding': True
			}
		}
		
		# 기존 파일이 있으면 백업
		if worker_config_path.exists():
			backup_path = worker_config_path.with_suffix('.yaml.backup')
			if not backup_path.exists():
				with open(backup_path, 'w', encoding='utf-8') as f:
					yaml.dump(ffmpeg_worker_config, f, default_flow_style=False, allow_unicode=True)
		
		# FFmpeg 전용 Worker 설정 저장
		with open(worker_config_path, 'w', encoding='utf-8') as f:
			yaml.dump(ffmpeg_worker_config, f, default_flow_style=False, allow_unicode=True)
		
		print("FFmpeg 전용 Worker 설정이 생성되었습니다.")
		
	except Exception as e:
		print(f"FFmpeg Worker 설정 생성 오류: {e}")

def _setup_ffmpeg_structure(flamenco_dir: Path) -> None:
	"""FFmpeg 전용 폴더 구조를 생성합니다. (V3: 기존 구조는 건드리지 않음)"""
	# FFmpeg 전용 디렉토리 생성
	ffmpeg_directories = [
		'ffmpeg-jobs',
		'ffmpeg-logs',
		'ffmpeg-output',
		'ffmpeg-temp'
	]
	
	created_dirs = []
	for dir_name in ffmpeg_directories:
		dir_path = flamenco_dir / dir_name
		if not dir_path.exists():
			dir_path.mkdir(exist_ok=True)
			created_dirs.append(dir_name)
	
	if created_dirs:
		print(f"생성된 FFmpeg 전용 디렉토리: {', '.join(created_dirs)}")
	else:
		print("모든 FFmpeg 전용 디렉토리가 이미 존재합니다.")

def _setup_manager_config(manager_config_path: Path) -> None:
	"""Manager 설정을 FFmpeg Encoder에 맞게 수정합니다. (Legacy - V2용)"""
	try:
		with open(manager_config_path, 'r', encoding='utf-8') as f:
			config = yaml.safe_load(f)
		
		# 기존 설정이 없으면 빈 딕셔너리로 초기화
		if config is None:
			config = {}
		
		# FFmpeg 관련 설정이 이미 있는지 확인
		ffmpeg_exists = False
		if 'variables' in config and 'ffmpeg' in config['variables']:
			ffmpeg_exists = True
		
		# FFmpeg 설정이 없을 때만 추가
		if not ffmpeg_exists:
			# variables 섹션이 없으면 생성
			if 'variables' not in config:
				config['variables'] = {}
			
			# FFmpeg 변수 추가
			config['variables']['ffmpeg'] = {
				'values': [
					{'platform': 'windows', 'value': 'ffmpeg'},
					{'platform': 'linux', 'value': 'ffmpeg'},
					{'platform': 'darwin', 'value': 'ffmpeg'}
				]
			}
			
			# 설정 파일 백업 (기존 백업이 없을 때만)
			backup_path = manager_config_path.with_suffix('.yaml.backup')
			if not backup_path.exists():
				with open(backup_path, 'w', encoding='utf-8') as f:
					yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
			
			# 수정된 설정 저장
			with open(manager_config_path, 'w', encoding='utf-8') as f:
				yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
			
			print("Manager 설정에 FFmpeg 변수가 추가되었습니다.")
		else:
			print("Manager 설정에 FFmpeg 변수가 이미 존재합니다.")
			
	except Exception as e:
		print(f"Manager 설정 수정 오류: {e}")

def _setup_worker_config(worker_config_path: Path) -> None:
	"""Worker 설정 파일을 생성하거나 업데이트합니다. (Legacy - V2용)"""
	try:
		# 기존 설정 파일이 있는지 확인
		if worker_config_path.exists():
			with open(worker_config_path, 'r', encoding='utf-8') as f:
				config = yaml.safe_load(f)
			
			# 기존 설정이 없으면 빈 딕셔너리로 초기화
			if config is None:
				config = {}
			
			# FFmpeg 관련 설정이 이미 있는지 확인
			ffmpeg_exists = False
			if 'variables' in config and 'ffmpeg' in config['variables']:
				ffmpeg_exists = True
			
			# FFmpeg 설정이 없을 때만 추가
			if not ffmpeg_exists:
				# variables 섹션이 없으면 생성
				if 'variables' not in config:
					config['variables'] = {}
				
				# FFmpeg 변수 추가
				config['variables']['ffmpeg'] = {
					'values': [
						{'platform': 'windows', 'value': 'ffmpeg'},
						{'platform': 'linux', 'value': 'ffmpeg'},
						{'platform': 'darwin', 'value': 'ffmpeg'}
					]
				}
				
				# 설정 파일 백업 (기존 백업이 없을 때만)
				backup_path = worker_config_path.with_suffix('.yaml.backup')
				if not backup_path.exists():
					with open(backup_path, 'w', encoding='utf-8') as f:
						yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
				
				# 수정된 설정 저장
				with open(worker_config_path, 'w', encoding='utf-8') as f:
					yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
				
				print("Worker 설정에 FFmpeg 변수가 추가되었습니다.")
			else:
				print("Worker 설정에 FFmpeg 변수가 이미 존재합니다.")
		else:
			# 기존 파일이 없으면 새로 생성
			worker_config = {
				'manager_url': 'http://localhost:8080',
				'worker_name': 'ffmpeg-worker',
				'worker_tags': ['ffmpeg'],
				'variables': {
					'ffmpeg': {
						'values': [
							{'platform': 'windows', 'value': 'ffmpeg'},
							{'platform': 'linux', 'value': 'ffmpeg'},
							{'platform': 'darwin', 'value': 'ffmpeg'}
						]
					}
				}
			}
			
			with open(worker_config_path, 'w', encoding='utf-8') as f:
				yaml.dump(worker_config, f, default_flow_style=False, allow_unicode=True)
			
			print("새로운 Worker 설정 파일이 생성되었습니다.")
			
	except Exception as e:
		print(f"Worker 설정 생성/수정 오류: {e}")

def _setup_ffmpeg_job_type(scripts_dir: Path) -> None:
	"""FFmpeg 작업 타입 스크립트를 생성합니다."""
	# Flamenco 3.7용 FFmpeg 작업 컴파일러 (JavaScript)
	# 공식 문서에 따르면 JavaScript 파일이어야 함
	ffmpeg_compiler_script = """const JOB_TYPE = {
    label: "FFmpeg Video Encoding",
    settings: [
        { key: "command", type: "string", required: true, label: "FFmpeg Command" },
        { key: "working_directory", type: "string", default: ".", label: "Working Directory" },
        { key: "input_files", type: "string", label: "Input Files" },
        { key: "output_file", type: "string", label: "Output File" },
    ]
};

function compileJob(job) {
    const settings = job.settings;
    
    // FFmpeg 작업 생성 (exec 명령어 사용)
    const ffmpegTask = author.Task("ffmpeg_encode", "misc");
    
    // FFmpeg 명령어를 exec 명령어로 실행
    const commandParts = settings.command.split(' ');
    const executable = commandParts[0];
    const args = commandParts.slice(1);
    
    ffmpegTask.addCommand(author.Command("exec", {
        exe: executable,
        args: args,
    }));
    
    job.addTask(ffmpegTask);
}
"""
	
	# FFmpeg 작업 컴파일러 스크립트 생성 (JavaScript)
	# Flamenco 3.7에서는 파일명이 작업 타입과 일치해야 함
	compiler_path = scripts_dir / "ffmpeg-encode.js"
	if not compiler_path.exists():
		with open(compiler_path, 'w', encoding='utf-8') as f:
			f.write(ffmpeg_compiler_script)
		print("FFmpeg 작업 컴파일러 스크립트(JavaScript)가 생성되었습니다.")
	else:
		print("FFmpeg 작업 컴파일러 스크립트가 이미 존재합니다.")
	
	# Python 백업 컴파일러도 생성 (호환성을 위해)
	python_compiler_script = """#!/usr/bin/env python3
\"\"\"
FFmpeg 작업 컴파일러 (Flamenco 3.7)
Flamenco에서 FFmpeg 인코딩 작업을 처리합니다.
\"\"\"

import os
import sys
import json
from pathlib import Path

def compile_job(job_settings: dict) -> dict:
	\"\"\"FFmpeg 작업을 컴파일합니다.\"\"\"
	
	# 기본 설정
	command = job_settings.get('command', [])
	files = job_settings.get('input_files', [])
	working_directory = job_settings.get('working_directory', '.')
	
	if not command:
		raise ValueError("FFmpeg 명령어가 없습니다")
	
	# 작업 생성
	tasks = []
	
	# FFmpeg 작업 생성
	ffmpeg_task = {
		'type': 'ffmpeg',
		'name': 'FFmpeg 인코딩',
		'commands': [{
			'executable': 'ffmpeg',
			'args': command if isinstance(command, str) else ' '.join(command),
			'cwd': working_directory
		}],
		'depends_on': []
	}
	
	tasks.append(ffmpeg_task)
	
	return {
		'tasks': tasks,
		'job_type': 'ffmpeg',
		'name': job_settings.get('name', 'FFmpeg 인코딩 작업')
	}

if __name__ == '__main__':
	# JSON 입력 읽기
	input_data = json.loads(sys.stdin.read())
	
	try:
		result = compile_job(input_data)
		print(json.dumps(result, ensure_ascii=False, indent=2))
	except Exception as e:
		print(f"오류: {e}", file=sys.stderr)
		sys.exit(1)
"""
	
	# Python 백업 컴파일러 생성
	python_compiler_path = scripts_dir / "ffmpeg-job-compiler.py"
	if not python_compiler_path.exists():
		with open(python_compiler_path, 'w', encoding='utf-8') as f:
			f.write(python_compiler_script)
		
		# 실행 권한 부여 (Unix 시스템)
		if os.name != 'nt':
			os.chmod(python_compiler_path, 0o755)
		
		print("FFmpeg Python 백업 컴파일러가 생성되었습니다.")
	else:
		print("FFmpeg Python 백업 컴파일러가 이미 존재합니다.")

def _setup_flamenco_structure(flamenco_dir: Path) -> None:
	"""Flamenco 폴더 구조를 생성합니다. (Legacy - V2용)"""
	# 필요한 디렉토리 생성
	directories = [
		'jobs',
		'logs',
		'storage',
		'scripts',
		'workers'
	]
	
	created_dirs = []
	for dir_name in directories:
		dir_path = flamenco_dir / dir_name
		if not dir_path.exists():
			dir_path.mkdir(exist_ok=True)
			created_dirs.append(dir_name)
	
	if created_dirs:
		print(f"생성된 디렉토리: {', '.join(created_dirs)}")
	else:
		print("모든 필요한 디렉토리가 이미 존재합니다.")

def load_flamenco_config(flamenco_path: str) -> FlamencoAutoConfig:
	"""Flamenco 설치 경로에서 설정을 자동으로 읽어옵니다."""
	try:
		# flamenco-manager.yaml 파일 경로 찾기
		config_paths = [
			Path(flamenco_path) / "flamenco-manager.yaml",
			Path(flamenco_path) / "manager" / "flamenco-manager.yaml",
			Path(flamenco_path) / "flamenco" / "flamenco-manager.yaml",
		]
		
		config_file = None
		for path in config_paths:
			if path.exists():
				config_file = path
				break
		
		if not config_file:
			return FlamencoAutoConfig(
				base_url="",
				token="",
				manager_name="",
				listen_port=8080,
				success=False,
				error_message="flamenco-manager.yaml 파일을 찾을 수 없습니다."
			)
		
		# YAML 파일 읽기
		with open(config_file, 'r', encoding='utf-8') as f:
			config = yaml.safe_load(f)
		
		# 설정 추출
		manager_name = config.get('manager_name', 'Flamenco')
		listen = config.get('listen', ':8080')
		api_token = config.get('api_token', '')
		
		# listen 포트 파싱 (:8080 -> 8080)
		if isinstance(listen, str) and listen.startswith(':'):
			port = int(listen[1:])
		else:
			port = 8080
		
		# 기본 URL 생성 (실제 IP 주소 사용)
		# listen 설정에서 IP 주소 추출 시도
		if isinstance(listen, str):
			if ':' in listen:
				# :8080 형태인 경우 localhost 사용
				if listen.startswith(':'):
					base_url = f"http://localhost:{port}"
				else:
					# 192.168.1.100:8080 형태인 경우 해당 IP 사용
					ip_part = listen.split(':')[0]
					base_url = f"http://{ip_part}:{port}"
			else:
				base_url = f"http://localhost:{port}"
		else:
			base_url = f"http://localhost:{port}"
		
		return FlamencoAutoConfig(
			base_url=base_url,
			token=api_token,
			manager_name=manager_name,
			listen_port=port,
			success=True
		)
		
	except Exception as e:
		return FlamencoAutoConfig(
			base_url="",
			token="",
			manager_name="",
			listen_port=8080,
			success=False,
			error_message=f"설정 파일 읽기 오류: {str(e)}"
		)


class FlamencoClient:
	def __init__(self, cfg: FlamencoConfig) -> None:
		self.base_url = cfg.base_url.rstrip("/")
		self.session = requests.Session()
		self.session.headers.update({
			"Authorization": f"Bearer {cfg.token}",
			"Content-Type": "application/json",
		})

	def submit_ffmpeg_job(self, title: str, command: list[str], files: list[str], output_path: str = None) -> Dict[str, Any]:
		print(f"[DEBUG] Submitting Flamenco job: {title}")
		print(f"[DEBUG] Command: {' '.join(command)}")
		print(f"[DEBUG] Files: {files}")
		print(f"[DEBUG] Output path: {output_path}")
		
		# Get platform and convert to lowercase
		platform = get_submitter_platform().lower()
		print(f"[DEBUG] Platform: {platform}")
		
		# Flamenco 3.7에서 사용 가능한 작업 타입들을 순서대로 시도
		command_str = " ".join(command)
		working_dir = str(Path(files[0]).parent) if files else "."
		print(f"[DEBUG] Working directory: {working_dir}")
		
		# Flamenco 3.7에서 사용 가능한 작업 타입들 (공식 문서 기준)
		job_types_to_try = [
			"ffmpeg-encode",  # 커스텀 FFmpeg 작업 타입
		]
		
		last_error = None
		
		for job_type in job_types_to_try:
			try:
				if job_type == "ffmpeg-encode":
					# 커스텀 FFmpeg 작업 타입
					payload = {
						"name": title,
						"type": job_type,
						"priority": 50,
						"settings": {
							"command": command_str,
							"working_directory": working_dir,
							"input_files": files,
							"output_file": output_path or (str(Path(files[0]).with_suffix('.mp4')) if files else "output.mp4"),
						},
						"submitter_platform": platform,
						"metadata": {
							"project": "FFmpeg Encoder",
							"user.name": "FFmpeg Encoder User",
							"user.email": "user@example.com"
						}
					}
				else:  # ffmpeg-encode
					# 커스텀 FFmpeg 작업 타입
					payload = {
						"name": title,
						"type": job_type,
						"priority": 50,
						"settings": {
							"command": command_str,
							"working_directory": working_dir,
							"input_files": files,
							"output_file": output_path or (str(Path(files[0]).with_suffix('.mp4')) if files else "output.mp4"),
						},
						"submitter_platform": platform,
						"metadata": {
							"project": "FFmpeg Encoder",
							"user.name": "FFmpeg Encoder User",
							"user.email": "user@example.com"
						}
					}
				
				r = self.session.post(f"{self.base_url}/api/v3/jobs", json=payload, timeout=30)
				r.raise_for_status()
				return r.json()
				
			except Exception as e:
				last_error = e
				continue
		
		# 모든 작업 타입이 실패한 경우 마지막 에러를 발생
		raise last_error or Exception("모든 작업 타입이 실패했습니다.")

	def get_job(self, job_id: str) -> Dict[str, Any]:
		r = self.session.get(f"{self.base_url}/api/v3/jobs/{job_id}", timeout=15)
		r.raise_for_status()
		return r.json()

	def wait_until_finished(self, job_id: str, poll_seconds: float = 3.0, timeout_seconds: float = 0) -> Dict[str, Any]:
		start = time.time()
		while True:
			job = self.get_job(job_id)
			state = job.get("state") or job.get("status")
			if state in {"finished", "failed", "canceled", "completed"}:
				return job
			time.sleep(poll_seconds)
			if timeout_seconds and (time.time() - start) > timeout_seconds:
				return job
