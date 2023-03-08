import simpy
import numpy as np
import matplotlib.pyplot as plt
import functools
import random
import threading
import logging
import time
import sys

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
    def __init__(self, id,  adist, sdist,N_max, initial_delay=0, finish=float("inf"),rate=1,slice_type=None):
        self.id = id
        self.type = slice_type
        
        self.adist = adist
        self.sdist = sdist
        self.initial_delay = initial_delay
        self.finish = finish
        self.files_sent = 0
        
        self.rate=rate
        self.N=0
        self.user_list=[]
        self.event_list=[]
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
        self.N+=1
        logging.info("Slice id :"+str(self.id)+" | User "+str(id)+ " joined. Packet size to send : "+str(packet_size)+" Interrupting ongoing connections.")
        for i,event in enumerate(self.event_list):
            if(i!=id) and  not (i in self.done_users):
                event.set()
                time.sleep(0.15)
                event.clear()
                
        
        
        start_time=time.time()
        logging.info("Slice id :"+str(self.id)+" | N is equal to : "+str(self.N))
        transmit=True

        while(transmit):
            try:
                start_time=time.time()
                #TODO add ressource usage
                user_rate=self.rate/self.N
                logging.info("Slice id :"+str(self.id)+" | User "+str(id)+ "  Rate is "+str(user_rate))
                time_to_send=packet_size/user_rate

                #Redundency to insure good functionning
                if(time_to_send<0):
                    self.N=self.N-1
                    self.files_sent += 1
                
                    self.time_list.append(time.time())
                    self.sent_list.append(self.files_sent)

                    self.done_users.append(id)
                    transmit=False
                    logging.info("Slice id :"+str(self.id)+" | User "+str(id)+ " disconnected")
                    break
                #######################################
               
                time.sleep(0.1)

                #Send file. Interrupt if event is activated
                self.event_list[id].wait(time_to_send)

                #If reallocation event was activated reallocate
                if(self.event_list[id].is_set()):
                    raise ConnectionAbortedError()

                self.N=self.N-1
                self.files_sent += 1
                
                self.time_list.append(time.time())
                self.sent_list.append(self.files_sent)

                self.done_users.append(id)
                transmit=False
                logging.info("Slice id :"+str(self.id)+" | User "+str(id)+ " disconnected")
            except ConnectionAbortedError:
                #Change data rate and retransmit
                logging.info("Slice id :"+str(self.id)+" | REALLOCATING for user "+str(id)+" with "+ str(self.N)+" users ")
                #Calculate size left
                time_remaining=time_to_send-time.time()+start_time
                packet_size=time_remaining*user_rate
                logging.info("Slice id :"+str(self.id)+" | Remaining size for user "+str(id)+" : "+str(packet_size))

        #Reallocate at disconnection
        for i,event in enumerate(self.event_list):
            if(i!=id) and  not (i in self.done_users):
                
                event.set()
                time.sleep(0.1)
                event.clear()
                

    def run(self):
        """The generator function used in simulations.
        """
        logging.info("\033[92m"+"Running "+str(self.id)+"\033[00m")
        counter=0
        
        while not simulation_status.is_set():
            # wait for next connection
            time.sleep(self.adist())

            #create a new user and append to user list
            if(len(self.user_list)-len(self.done_users))<=self.N_max:
                
                self.user_list.append(threading.Thread(target=self.slice_user,args=(counter,),daemon=True))
                self.event_list.append(threading.Event())
                self.user_list[-1].start()

                #increment user id
                counter+=1
        

class Network:
    def __init__(self,C):
        #self.env=env
        self.number_of_slices=5
        #self.capacity=simpy.Container(env,capacity=C,init=C)
        
        #Define the functions for data rates and interarrival rates

        #self.adist=[functools.partial(random.expovariate, 1/1.65),functools.partial(random.expovariate, 1/7.25),functools.partial(random.expovariate, 1/16),functools.partial(random.expovariate, 1/19),functools.partial(random.expovariate, 1/5)]
        self.adist=[functools.partial(random.expovariate, 1/3.65),functools.partial(random.expovariate, 1/1.2)]
        #self.sdist=[functools.partial(random.expovariate, 1/0.3),functools.partial(random.expovariate, 1/1.2),functools.partial(random.expovariate, 1/2.5),functools.partial(random.expovariate, 1/5),functools.partial(random.expovariate, 1)]
        self.sdist=[functools.partial(random.expovariate, 1/20),functools.partial(random.expovariate, 1/0.8)]
        
        self.slice1= Slice( "\033[93m"+"Slice1"+"\033[00m", self.adist[0], self.sdist[0],10)
        self.slice2= Slice( "\033[96m"+"Slice2"+"\033[00m", self.adist[1], self.sdist[1],10)

        self.thread1=threading.Thread(target=self.slice1.run,daemon=True)
        self.thread2=threading.Thread(target=self.slice2.run,daemon=True)
    
    def run(self,t):
        #self.env.run(until=time)
        self.thread1.start()
        self.thread2.start()

        time.sleep(t)
        simulation_status.set()

        #TODO add graph saving option
        if(False):
            fig,ax = plt.subplots()
            ax.plot(self.slice1.time_list,self.slice1.sent_list)
            plt.show()
        #print("main thread done")
        logging.info("\033[92m"+"Network simulation complete"+"\033[00m")

if __name__ == '__main__':
    if len(sys.argv)!=2:
        raise AttributeError("Input simulation time in seconds as an argument")
    try:
        simulation_time=int(sys.argv[1])
    except TypeError:
        raise TypeError("Input has to be an integer")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S"
    )
    
    simulation_status=threading.Event()
    net=Network(8000)
    net.run(simulation_time)
    






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