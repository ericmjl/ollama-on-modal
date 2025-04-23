# Deploy Ollama on Modal

This is derived from @irfansharif's [ollama-modal](https://github.com/irfansharif/ollama-modal) repository.
Thank you @irfansharif for the great work!

I have modified it to be an OpenAI-compatible endpoint that allows [llamabot](https://github.com/ericmjl/llamabot) to connect to the modal endpoint seamlessly.
It supports streaming and non-streaming responses.

To deploy the app, run the following command (if you have `modal` installed already):

```bash
modal deploy endpoint_v2.py
```

No further development is planned for this repository;
it's just here as a reference for others who want to deploy Ollama on Modal!
Meanwhile, I will be moving most of this code into the [llamabot](https://github.com/ericmjl/llamabot) repository
and continue development there.
