class PlatformError(Exception):
 def __init__(self,code,*,retryable=False,status=None):
  self.code=code;self.retryable=retryable;self.status=status
  super().__init__(code)
 def safe(self):return {'code':self.code,'retryable':self.retryable,'http_status':self.status}
