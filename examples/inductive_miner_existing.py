from pm4pydistr.remote_wrapper import factory as wrapper_factory

wrapper = wrapper_factory.apply("137.226.117.71", "5001", "hello", "receipt")
print(wrapper.calculate_im_existing_log())
