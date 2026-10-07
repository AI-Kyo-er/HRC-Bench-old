"""思考内容自由生成，仅在实际思考结束后约束当前调用的JSON结构。"""


class ThinkingSchemaFilter:
    def __init__(self,json_filter,*,input_length,close_think_id,tool_prefix_ids,vocab_size,eos_id,thinking_limit=1536):
        self.json_filter=json_filter;self.input_length=input_length
        self.close_think_id=close_think_id;self.tool_prefix_ids=list(tool_prefix_ids)
        self.free_tokens=[i for i in range(vocab_size) if i!=eos_id]
        self.thinking_limit=thinking_limit;self.forced_think_close=False
        self.json_start_index=None

    def __call__(self,batch_id,sent):
        generated=sent.tolist()[self.input_length:]
        if self.close_think_id not in generated:
            if len(generated)>=self.thinking_limit:
                self.forced_think_close=True
                return [self.close_think_id]
            return self.free_tokens
        close=generated.index(self.close_think_id)
        prefix_count=len(generated)-close-1
        if prefix_count<len(self.tool_prefix_ids):return [self.tool_prefix_ids[prefix_count]]
        self.json_start_index=self.input_length+close+1+len(self.tool_prefix_ids)
        return self.json_filter(batch_id,sent)
