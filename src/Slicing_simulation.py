import simpy
import numpy as np
import matplotlib.pyplot as plt
import functools
import random
import threading
import logging
import time
import sys
import cvxpy as cp

#TODO add capacity checking and requesting from central ressource
class Slice(object):
    """ Slice of an antenna. Simulates traffic that arrives each adist() and requests a file with sdist() size.

        Parameters
        ----------
        adist : function
            a no parameter function that returns the successive inter-arrival times of connections
        sdist : function
            a no parameter function that returns the successive sizes of the files to be transferred
        C : Central ressource
            Central capacity of the antenna
        rate : data rate
        N : number of active users
            starts at 0, increases after each active thread
        slice_type: Type of slice
        N_max: maximum number of users

    """
    def __init__(self, id,  adist, sdist,N_max,rate=1):
        self.id = id    
        self.adist = adist
        self.sdist = sdist
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

            # create a new user and append to user list
            if(len(self.user_list)-len(self.done_users))<=self.N_max:
                
                self.user_list.append(threading.Thread(target=self.slice_user,args=(counter,),daemon=True))
                self.event_list.append(threading.Event())
                self.user_list[-1].start()

                # increment user id
                counter+=1
        

class Network:
    """Class defining the network and its slices

        Parameters
        ----------
        C: Central capacity of the network
        t: Simulation time

    """
    def __init__(self,C,t):
        self.simulation_time=t
        #TODO set central capacity
        self.C=C
        

        #Define the functions for data rates and interarrival rates
        self.adist=[functools.partial(random.expovariate, 1/3.65),functools.partial(random.expovariate, 1/1.2)]
        self.sdist=[functools.partial(random.expovariate, 1/20),functools.partial(random.expovariate, 1/0.8)]
        
        self.slice1= Slice( "\033[93m"+"Slice1"+"\033[00m", self.adist[0], self.sdist[0],10)
        self.slice2= Slice( "\033[96m"+"Slice2"+"\033[00m", self.adist[1], self.sdist[1],10)

        self.thread1=threading.Thread(target=self.slice1.run,daemon=True)
        self.thread2=threading.Thread(target=self.slice2.run,daemon=True)
    
    def run(self):
        self.thread1.start()
        self.thread2.start()

        time.sleep(self.simulation_time)
        simulation_status.set()

        #TODO add graph saving option
        if(False):
            fig,ax = plt.subplots()
            ax.plot(self.slice1.time_list,self.slice1.sent_list)
            plt.show()
        
        logging.info("\033[92m"+"Network simulation complete"+"\033[00m")


def solve_optimisation(Ns,C,Rmin,Rmax):
    """Function for solving the allocation problem

        Parameters
        ----------
        Ns : vector of active user per slice
        C : Available common capacity
        Rmin : minimum data rate per slice
        Rmax : maximum data rate per slice
    """

    #Define Variable to be resolved
        #The variable is Cs. Its a vector of size 2
    x=cp.Variable(2)
    
    #Construct the problem
    objective = cp.Maximize(cp.sum(W_func(Ns, Ncont)@np.divide(x/Ns)))
    constraints=[np.dot(x,Ns),x<=Rmax,x>=Rmin]
    prob = cp.Problem(objective=objective,constraints=constraints)
    
    #Solve the porblem
    prob.solve()

    #Return the value
    return x.value

def W_func(Ns,Ncont):
    """W function defined in the paper
    
        Parameters
        ----------
        Ncont: array of maximum number of active users per slice
        Ns : array number of active users in the slice
    """
    assert len(Ns)==len(Ncont)==number_of_slices
    result=[]
    for i in range(len(Ns)):
        if(Ns[i]<=Ncont[i]):
            result.append(1)
        else:
            result.append(Ncont[i]/Ns[i])
    return result
    
#TODO define allocation schemes

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
    net=Network(8000,simulation_time)
    number_of_slices=2
    net.run()