import streamlit as st
import sys
import os
from streamlit.web import cli as stcli
from streamlit import runtime
import io
from contextlib import redirect_stdout, redirect_stderr

def run_streamlit():
    # Set Streamlit configuration for serverless environment
    os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
    os.environ['STREAMLIT_SERVER_PORT'] = '3000'
    os.environ['STREAMLIT_SERVER_ENABLE_CORS'] = 'false'
    os.environ['STREAMLIT_SERVER_ENABLE_XSRF'] = 'false'
    
    # Set your AWS credentials from Vercel Environment Variables
    os.environ['AWS_ACCESS_KEY_ID'] = os.getenv('AWS_ACCESS_KEY_ID', '')
    os.environ['AWS_SECRET_ACCESS_KEY'] = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    os.environ['AWS_DEFAULT_REGION'] = os.getenv('AWS_DEFAULT_REGION', 'eu-west-1')
    
    # Redirect Streamlit output
    f = io.StringIO()
    with redirect_stdout(f), redirect_stderr(f):
        try:
            # Run your main Streamlit app
            sys.argv = ["streamlit", "run", "app.py", 
                       "--server.port=3000",
                       "--server.enableCORS=false",
                       "--server.enableXsrfProtection=false"]
            
            if runtime.exists():
                # App is already running
                return "App is running"
            else:
                # Start the app
                stcli.main()
        except SystemExit:
            pass
        except Exception as e:
            return f"Error: {str(e)}"
    
    return f.getvalue()

def handler(request):
    """Vercel serverless function handler"""
    try:
        result = run_streamlit()
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'text/html',
            },
            'body': result
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f'Error running Streamlit app: {str(e)}'
        }

# For local testing
if __name__ == '__main__':
    print(handler(None))