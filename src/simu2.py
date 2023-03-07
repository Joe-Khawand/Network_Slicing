import simpy
import numpy as np
import matplotlib.pyplot as plt
import functools
import random
import threading
import logging
from simpy import Interrupt

#TODO add capacity checking and requesting from central ressource
class Slice(object):
    """ Slice of an antenna. Simulates traffic that arrives each adist() and requests a file with sdist() size.

        Parameters
        ----------
        env : simpy.Environment
            the simulation environment
        adist : function
            a no parameter function that returns the successive inter-arrival times of connections
        sdist : function
            a no parameter function that returns the successive sizes of the files to be transferred
        initial_delay : number
            Starts generation after an initial delay. Default = 0
        finish : number
            Stops generation at the finish time. Default is infinite
        C : simpy ressource
            Central capacity of the antenna
        rate : data rate
        N : number of active users
            starts at 0, increases after each active thread
        slice_type: Type of slice
            can be ...
        N_max: maximum number of users

    """
    def __init__(self, env, id,  adist, sdist,N_max, initial_delay=0, finish=float("inf"),rate=0.1,slice_type=None):
        self.id = id
        self.type = slice_type
        self.env = env
        self.adist = adist
        self.sdist = sdist
        self.initial_delay = initial_delay
        self.finish = finish
        self.files_sent = 0
        self.action = env.process(self.run())  # starts the run() method as a SimPy process
        self.rate=rate
        self.N=0
        self.user_list=[]
        self.done_users=[]
        self.N_max=N_max
        #TODO add lists for graphs and statistics 

        #graphing
        self.time_list=[]
        self.sent_list=[]


    def slice_user(self,id):
        """Simulation of a user connceting to the slice and requesting download
        """
        packet_size=self.sdist()
        logging.info("Slice id :"+str(self.id)+" | User "+str(id)+ " joined.Packet size to send : "+str(packet_size)+" Interrupting ongoing connections.")
        for i,user in enumerate(self.user_list):
            if(i!=id) and  not (i in self.done_users):
                try:
                    self.user_list[i].interrupt()
                except:
                    pass
        
        self.N+=1
        start_time=self.env.now
        logging.info("Slice id :"+str(self.id)+" | N is equal to : "+str(self.N))
        transmit=True

        while(transmit):
            try:
                start_time=self.env.now
                #TODO add ressource usage
                user_rate=self.rate/self.N
                time_to_send=packet_size/user_rate
                
                yield self.env.timeout(time_to_send)
                self.N=self.N-1
                self.files_sent += 1
                
                self.time_list.append(self.env.now)
                self.sent_list.append(self.files_sent)

                self.done_users.append(id)
                transmit=False
                logging.info("Slice id :"+str(self.id)+" | User "+str(id)+ " disconnected")
            except Interrupt:
                #Change data rate and retransmit
                logging.info("Slice id :"+str(self.id)+" | REALLOCATING for user "+str(id)+" with "+ str(self.N)+" users ")
                #Calculate size left
                time_remaining=time_to_send-self.env.now+start_time
                packet_size=time_remaining*user_rate
                logging.info("Slice id :"+str(self.id)+" | Remaining size for user "+str(id)+" : "+str(packet_size))

        #Reallocate at disconnection
        for i,user in enumerate(self.user_list):
            if(i!=id) and  not (i in self.done_users):
                try:
                    self.user_list[i].interrupt()
                except:
                    pass
                

    def run(self):
        """The generator function used in simulations.
        """
        counter=0
        #yield self.env.timeout(self.initial_delay)
        while self.env.now < self.finish:
            # wait for next transmission
            yield self.env.timeout(self.adist())

            #create a new user and append to user list
            if(len(self.user_list)-len(self.done_users))<=self.N_max:
                self.user_list.append(self.env.process(self.slice_user(counter)))
                #increment user id
                counter+=1
        
        
           


class Network:
    def __init__(self,env,C,infoging):
        self.env=env
        self.number_of_slices=5
        self.capacity=simpy.Container(env,capacity=C,init=C)
        
        #Define the functions for data rates and interarrival rates
        self.adist=[functools.partial(random.expovariate, 1/1.65),functools.partial(random.expovariate, 1/7.25),functools.partial(random.expovariate, 1/16),functools.partial(random.expovariate, 1/19),functools.partial(random.expovariate, 1/5)]
        self.sdist=[functools.partial(random.expovariate, 1/0.3),functools.partial(random.expovariate, 1/1.2),functools.partial(random.expovariate, 1/2.5),functools.partial(random.expovariate, 1/5),functools.partial(random.expovariate, 1)]

        self.slice1= Slice(self.env, "slice1", self.adist[0], self.sdist[0],50)
        self.slice2= Slice(self.env, "slice2", self.adist[1], self.sdist[1],50)
        self.slice3= Slice(self.env, "slice3", self.adist[2], self.sdist[2],50)
        self.slice4= Slice(self.env, "slice4", self.adist[3], self.sdist[3],50)
        self.slice5= Slice(self.env, "slice5", self.adist[4], self.sdist[4],50)
    
    def run(self,time):
        self.env.run(until=time)
        if(True):
            fig,ax = plt.subplots()
            ax.plot(self.slice3.time_list,self.slice3.sent_list)
            plt.show()

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S"
    )
    
    net=Network(simpy.Environment(), 8000,True)
    net.run(1000)






#    def re_transmit(self,size,time_to_send,s_time,user_rate,id,counter):
#        print("Restransmission number ", counter," for user ",id," with ", self.N," users ")
#        try:
#            #Calculate size left
#            time_remaining=time_to_send-self.env.now+s_time
#            size_remaining=time_remaining*user_rate
#            #Calculate new user rate
#            user_rate=self.rate/self.N
#
#            start_time=self.env.now
#            new_time_to_send=size/user_rate
#            yield self.env.timeout(new_time_to_send)
#        except Interrupt:
#            print("Restransmit")
#            self.re_transmit(size, time_to_send=new_time_to_send,s_time=start_time,user_rate=user_rate,id=id,counter=counter+1)